"""Development-only comparison, frozen selection and one separate reference evaluation."""

from datetime import datetime, timezone
import gc
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import yaml

from .identity import fingerprint
from .india_dataset import TASK, load_reference_frames
from .india_models import fit_admitted, load_estimator, predict_estimator, reference_metrics, save_estimator
from .model_records import verify_model_bundle
from .outcome_data import write_json
from .storage_proof import require


def model_code():
    return {name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ("india_models.py", "model_resources.py", "india_dataset.py")}


def _seal(path, manifest):
    manifest.update(schema_version="1", code=model_code(),
                    dependencies={name: version(name) for name in ("numpy", "pandas", "catboost", "torch", "psutil", "pyarrow")},
                    lock_sha256=sha256((Path(__file__).parents[3] / "uv.lock").read_bytes()).hexdigest())
    manifest["files"] = {file.name: sha256(file.read_bytes()).hexdigest()
                         for file in sorted(path.iterdir()) if file.is_file()}
    if manifest["kind"] == "india_reference_models":
        manifest["model_id"] = fingerprint({"selection": manifest["selection_id"], "code": manifest["code"],
                                             "files": manifest["files"], "dependencies": manifest["dependencies"]})
    write_json(path / "manifest.json", manifest)
    verify_model_bundle(path, manifest["kind"])
    return manifest


def train_reference_candidate(dataset, config_path, candidate, output):
    config = yaml.safe_load(Path(config_path).read_bytes())
    specification = config["reference_experiments"]["candidates"][candidate]
    manifest, frame = load_reference_frames(dataset)
    development = frame[frame.partition == "development"].copy()
    del frame
    parameters = {"seed": config["reference_training"]["seed"], **specification["parameters"]}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "specification.json", specification)
    folds, predictions = [], []
    try:
        for fold in range(manifest["split_specification"]["development_folds"]):
            train = development[development.fold != fold]
            validation = development[development.fold == fold]
            model, state = fit_admitted(train, validation, manifest["features"], specification["method"],
                                        parameters, specification.get("feature_groups"))
            values = predict_estimator(model, state, validation)
            prefix = f"fold-{fold}"
            save_estimator(model, state, output, prefix)
            restored, restored_state = load_estimator(output, prefix)
            replay = predict_estimator(restored, restored_state, validation)
            require(np.allclose(values, replay, atol=1e-7, rtol=0), "Saved development model does not replay")
            result = reference_metrics(validation, values)
            folds.append({"fold": fold, "metrics": result, "selected_iterations": state["selected_iterations"],
                          "reload_max_abs_error": float(np.abs(values - replay).max()),
                          "resources": state["resource_telemetry"]})
            part = validation[["example_id", "target_record_id", "fold"]].copy()
            part["prediction"] = values
            predictions.append(part)
            write_json(output / f"{prefix}.report.json", folds[-1])
            del model, restored, train, validation
            gc.collect()
        out_of_fold = pd.concat(predictions, ignore_index=True)
        require(not out_of_fold.example_id.duplicated().any() and
                set(out_of_fold.example_id) == set(development.example_id), "Incomplete out-of-fold predictions")
        merged = development.merge(out_of_fold[["example_id", "prediction"]], on="example_id", validate="one_to_one")
        report = {"candidate": candidate, "method": specification["method"], "dataset_id": manifest["dataset_id"],
                  "status": "development_only_no_test_evaluation", "folds": folds,
                  "mean_fold_macro_crop_mae": float(np.mean([row["metrics"]["macro_crop_mae_index_points"] for row in folds])),
                  "out_of_fold": reference_metrics(merged, merged.prediction),
                  "final_iterations": int(np.median([row["selected_iterations"] for row in folds]))}
        out_of_fold.to_parquet(output / "out_of_fold.parquet", index=False)
        write_json(output / "report.json", report)
        _seal(output, {"kind": "india_reference_candidate", "task": TASK, "candidate": candidate,
                       "dataset_id": manifest["dataset_id"], "specification": specification,
                       "dataset_manifest_sha256": sha256((Path(dataset) / "manifest.json").read_bytes()).hexdigest()})
        return {"candidate": candidate, "mean_fold_macro_crop_mae": report["mean_fold_macro_crop_mae"],
                "ndcg_at_5": report["out_of_fold"]["ndcg_at_5"], "output": str(output.resolve())}
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise


def masked_softmax(scores, mask, temperature):
    scores, mask = np.asarray(scores, dtype=float), np.asarray(mask, dtype=bool)
    require(scores.ndim == 1 and scores.shape == mask.shape, "Softmax score/mask shape differs")
    require(np.isfinite(scores).all() and np.isfinite(temperature) and temperature > 0,
            "Softmax requires finite scores and a positive temperature")
    result = np.zeros(len(scores), dtype=float)
    if mask.any():
        selected = scores[mask]
        weights = np.exp((selected - selected.max()) / temperature)
        result[mask] = weights / weights.sum()
    return result


def _temperature_fit(frame, prediction, definition):
    groups = list(frame.groupby(["context_id", "production_system"]).indices.values())
    teacher_temperature = definition["teacher_temperature"]
    truth = frame.target.to_numpy()
    losses = {}
    for temperature in definition["temperatures"]:
        loss = []
        for indices in groups:
            teacher = masked_softmax(truth[indices], np.ones(len(indices), dtype=bool), teacher_temperature)
            student = masked_softmax(prediction[indices], np.ones(len(indices), dtype=bool), temperature)
            loss.append(float(np.sum(teacher * (np.log(np.maximum(teacher, 1e-15)) -
                                                np.log(np.maximum(student, 1e-15))))))
        losses[str(temperature)] = float(np.mean(loss))
    best = min(definition["temperatures"], key=lambda value: (losses[str(value)], value))
    return {"temperature": best, "teacher_temperature": teacher_temperature, "reference_kl_by_temperature": losses,
            "interpretation": "relative_reference_preference_not_probability_of_farming_success",
            "fit_partition": "calibration", "candidate_scope": "all_source_supported_crops_at_one_cell_period_and_system"}


def finalize_reference_models(dataset, config_path, run_paths, output):
    config = yaml.safe_load(Path(config_path).read_bytes())
    protocol = config["reference_experiments"]
    dataset_manifest, frame = load_reference_frames(dataset)
    dataset = Path(dataset)
    runs = {}
    for path in map(Path, run_paths):
        manifest = verify_model_bundle(path, "india_reference_candidate")
        name = manifest["candidate"]
        require(name not in runs and name in protocol["candidates"], "Repeated or undeclared model candidate")
        require(manifest["dataset_id"] == dataset_manifest["dataset_id"] and manifest["code"] == model_code() and
                manifest["dataset_manifest_sha256"] == sha256((dataset / "manifest.json").read_bytes()).hexdigest(),
                "Candidate code or locked dataset differs")
        require(manifest["specification"] == protocol["candidates"][name], "Candidate differs from the declared search budget")
        report = json.loads((path / "report.json").read_bytes())
        oof = pd.read_parquet(path / "out_of_fold.parquet")
        expected = frame[frame.partition == "development"]
        require(not oof.example_id.duplicated().any() and set(oof.example_id) == set(expected.example_id),
                "Candidate lacks the complete development cohort")
        aligned = expected[["example_id", "fold"]].merge(oof, on="example_id", validate="one_to_one")
        require((aligned.fold_x == aligned.fold_y).all(), "Candidate development-fold membership differs")
        runs[name] = {"path": str(path.resolve()), "report": report,
                      "manifest_sha256": sha256((path / "manifest.json").read_bytes()).hexdigest()}
    require(runs.keys() == protocol["candidates"].keys(), "Complete every predeclared comparison before opening test")
    methods = {specification["method"] for specification in protocol["candidates"].values()}
    require(methods == {"baseline", "catboost", "mlp"}, "Three declared architecture families are required")
    selected = {method: min((name for name in runs if protocol["candidates"][name]["method"] == method),
                            key=lambda name: (runs[name]["report"]["mean_fold_macro_crop_mae"], name))
                for method in sorted(methods)}
    champion = min(selected, key=lambda method: (runs[selected[method]]["report"]["mean_fold_macro_crop_mae"], method))
    selection = {"dataset_id": dataset_manifest["dataset_id"], "selected_candidates": selected, "champion": champion,
                 "selection_metric": "mean_development_fold_macro_crop_MAE_index_points",
                 "candidate_development_scores": {name: item["report"]["mean_fold_macro_crop_mae"] for name, item in runs.items()},
                 "candidate_manifests": {name: item["manifest_sha256"] for name, item in runs.items()},
                 "calibration_definition": protocol["calibration"], "test_used_for_selection": False}
    selection["selection_id"] = fingerprint(selection)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "selection.json", selection)
    development = frame[frame.partition == "development"]
    calibration = frame[frame.partition == "calibration"]
    states, calibrations, calibration_predictions = {}, {}, []
    try:
        for method, candidate in selected.items():
            specification = protocol["candidates"][candidate]
            parameters = {"seed": config["reference_training"]["seed"], **specification["parameters"]}
            if method == "catboost":
                parameters["iterations"] = runs[candidate]["report"]["final_iterations"]
            elif method == "mlp":
                parameters["epochs"] = runs[candidate]["report"]["final_iterations"]
            model, state = fit_admitted(development, None, dataset_manifest["features"], method,
                                        parameters, specification.get("feature_groups"))
            if method == "baseline":
                state["features"] = state["categorical"] = ["crop_id", "production_system"]
                state["numeric"] = []
                state["dropped"] = {name: "median_baseline_uses_only_crop_and_system"
                                    for name in dataset_manifest["features"] if name not in state["features"]}
            state["numeric_support"] = {name: {"min": float(development[name].min()),
                                               "max": float(development[name].max())} for name in state["numeric"]}
            save_estimator(model, state, output, method)
            prediction = predict_estimator(model, state, calibration)
            fitted = _temperature_fit(calibration, prediction, protocol["calibration"])
            fitted["residual_90pct_by_crop"] = {
                crop: float(np.quantile(np.abs(prediction[indices] - calibration.target.to_numpy()[indices]), 0.9))
                for crop, indices in calibration.groupby("crop_id").indices.items()}
            fitted["interval_semantics"] = "empirical_calibration_reference_error_not_guaranteed_farm_coverage"
            calibrations[method], states[method] = fitted, state
            part = calibration[["example_id", "target_record_id"]].copy()
            part["method"], part["prediction"] = method, prediction
            calibration_predictions.append(part)
            write_json(output / (method + ".calibration.json"), fitted)
            del model
            gc.collect()
        pd.concat(calibration_predictions, ignore_index=True).to_parquet(output / "calibration_predictions.parquet", index=False)
        write_json(output / "evaluation_opened.json", {"selection_id": selection["selection_id"],
                                                      "opened_at": datetime.now(timezone.utc).isoformat()})
        test = frame[frame.partition == "test"]
        reports, test_predictions = {}, []
        for method, candidate in selected.items():
            model, state = load_estimator(output, method)
            prediction = predict_estimator(model, state, test)
            result = reference_metrics(test, prediction)
            widths = test.crop_id.map(calibrations[method]["residual_90pct_by_crop"]).to_numpy()
            result["empirical_residual_band_coverage"] = float((np.abs(prediction - test.target.to_numpy()) <= widths).mean())
            result["mean_residual_band_width_points"] = float(np.mean(np.minimum(1, prediction + widths) -
                                                                                    np.maximum(0, prediction - widths)) * 100)
            reports[method] = {"candidate": candidate, "development": runs[candidate]["report"]["out_of_fold"],
                               "mean_fold_macro_crop_mae": runs[candidate]["report"]["mean_fold_macro_crop_mae"],
                               "test": result, "resources": state["resource_telemetry"],
                               "features": state["features"], "dropped_features": state["dropped"]}
            part = test[["example_id", "target_record_id", "crop_id", "context_id", "production_system"]].copy()
            part["method"], part["prediction"] = method, prediction
            part["residual_width"] = widths
            test_predictions.append(part)
            del model
            gc.collect()
        pd.concat(test_predictions, ignore_index=True).to_parquet(output / "test_predictions.parquet", index=False)
        for name in ("contexts.parquet", "crops.parquet"):
            shutil.copyfile(dataset / name, output / name)
        context = pd.read_parquet(dataset / "contexts.parquet").set_index("context_id").loc[development.iloc[0].context_id]
        write_json(output / "example_request.json", {
            "schema_version": "1", "task": TASK, "mode": "historical_reference_analysis",
            "comparison_scope": "reference_climate_only", "context_id": development.iloc[0].context_id,
            "analysis_start": context["analysis_start"], "analysis_end": context["analysis_end"],
            "production_system": "HRLM", "crop_ids": ["gaez:MZE", "gaez:WHE", "gaez:GRD"],
        })
        report = {"status": "reference_models_trained_and_evaluated", "task": TASK,
                  "dataset_id": dataset_manifest["dataset_id"], "champion": champion, "models": reports,
                  "candidate_development_scores": selection["candidate_development_scores"],
                  "dataset_counts": dataset_manifest["counts"], "partition_rows": dataset_manifest["partition_rows"],
                  "test_spatial_groups": int(test.spatial_group.nunique()), "test_native_sites": int(test.site_id.nunique()),
                  "attribution": dataset_manifest["attribution"],
                  "limitations": [
                      "GAEZ reference-product distillation, not independent Indian farm validation.",
                      "Twenty-year historical climate contexts only; not arbitrary dates or a preplant forecast.",
                      "Softmax is relative preference, not a probability of agronomic success.",
                      "Modern soil groups and terrain are not historical field soil tests.",
                      "No actual field sequences, rotation effects, orchard ages or farmer-profit labels.",
                      "Crop traits remain source-qualified; trait availability does not establish India cultivation.",
                      "Correlated spatial reference records are not independent farms; error bands are descriptive.",
                      "CPU-only sequential training preserves other users' GPU allocation.",
                  ]}
        write_json(output / "report.json", report)
        final = _seal(output, {"kind": "india_reference_models", "task": TASK, "dataset_id": dataset_manifest["dataset_id"],
                              "model_id": fingerprint([selection["selection_id"], model_code()]), "champion": champion,
                              "periods": dataset_manifest["periods"], "features": dataset_manifest["features"],
                              "missing_requirement_axes": dataset_manifest["missing_requirement_axes"],
                              "attribution": dataset_manifest["attribution"],
                              "selection_id": selection["selection_id"], "strict_as_of_supported": False,
                              "preplant_supported": False, "rotation_effects_supported": False})
        return {"model_id": final["model_id"], "champion": champion,
                "test": {method: {key: reports[method]["test"][key] for key in
                                  ("mae_index_points", "rmse_index_points", "ndcg_at_5")} for method in reports},
                "output": str(output.resolve())}
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise
