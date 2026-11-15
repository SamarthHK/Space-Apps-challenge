"""Versioned, offline reference inference; unsupported field/time claims fail closed."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .identity import fingerprint
from .india_dataset import TASK, load_reference_frames
from .india_experiments import masked_softmax
from .india_inference_contract import ReferenceContextNotFound, ReferenceIntervalMismatch, ReferenceRequest
from .india_models import load_estimator, predict_estimator
from .model_records import verify_model_bundle
from .storage_proof import require


class ReferenceModel:
    def __init__(self, model_path, expected_model_id=None):
        path = Path(model_path)
        self.manifest = verify_model_bundle(path, "india_reference_models")
        manifest = self.manifest
        require(manifest["task"] == TASK, "Wrong trained task")
        require(expected_model_id is None or manifest["model_id"] == expected_model_id,
                "Configured reference model identity differs")
        require(manifest["model_id"] == fingerprint({
            "selection": manifest["selection_id"], "code": manifest["code"],
            "files": manifest["files"], "dependencies": manifest["dependencies"],
        }), "Reference model identity does not match its artifacts")
        method = manifest["champion"]
        require(method in ("baseline", "catboost", "mlp"), "Unsupported reference model method")
        required = {"contexts.parquet", "crops.parquet", method + ".state.json", method + ".calibration.json"}
        if method != "baseline":
            required.add(method + (".cbm" if method == "catboost" else ".pt"))
        require(required <= manifest["files"].keys(), "Reference model has unverified serving files")
        self.contexts = pd.read_parquet(path / "contexts.parquet").set_index("context_id", drop=False)
        self.crops = pd.read_parquet(path / "crops.parquet").set_index("crop_id")
        require(self.contexts.index.is_unique and self.crops.index.is_unique, "Repeated serving context or crop")
        self.model, self.state = load_estimator(path, method)
        require(self.state["method"] == method, "Reference checkpoint method differs from its manifest")
        self.calibration = json.loads((path / (method + ".calibration.json")).read_bytes())

    def predict(self, payload):
        return _predict_reference(self, payload)


def predict_reference(model_path, payload):
    return ReferenceModel(model_path).predict(payload)


def _predict_reference(loaded, payload):
    request = ReferenceRequest.model_validate(payload)
    manifest = loaded.manifest
    require(manifest["task"] == request.task == TASK, "Wrong trained task")
    if request.context_id not in loaded.contexts.index:
        raise ReferenceContextNotFound("Unknown reference context; arbitrary fields and dates are not supported")
    context = loaded.contexts.loc[request.context_id].to_dict()
    if (context["analysis_start"] != request.analysis_start.isoformat() or
            context["analysis_end"] != request.analysis_end.isoformat()):
        raise ReferenceIntervalMismatch("Requested interval differs from the reference context")
    crops = loaded.crops
    method = manifest["champion"]
    model, state, calibration = loaded.model, loaded.state, loaded.calibration
    support = {tuple(pair) for pair in state["crop_system_support"]}
    withheld, records = [], []
    for crop in request.crop_ids:
        reason = "excluded_by_farmer" if crop in request.excluded_crop_ids else \
            "no_target_bearing_training_support" if (crop, request.production_system) not in support else None
        if reason:
            withheld.append({"crop_id": crop, "reason": reason, "relative_preference": 0.0})
        else:
            require(crop in crops.index, "Trained crop is absent from the model registry snapshot")
            records.append({**context, **crops.loc[crop].to_dict(), "crop_id": crop,
                            "production_system": request.production_system})
    ranked, warnings = [], []
    if records:
        frame = pd.DataFrame(records)
        scores = predict_estimator(model, state, frame)
        mask = scores * 100 >= request.minimum_reference_score
        preferences = masked_softmax(scores, mask, calibration["temperature"])
        for index, row in enumerate(records):
            if not mask[index]:
                withheld.append({"crop_id": row["crop_id"], "reason": "below_requested_reference_score",
                                 "reference_score": float(scores[index] * 100), "relative_preference": 0.0})
                continue
            width = calibration["residual_90pct_by_crop"][row["crop_id"]]
            missing = [name for name in state["features"] if pd.isna(row[name])]
            outside = [name for name, limits in state.get("numeric_support", {}).items()
                       if not pd.isna(row[name]) and not limits["min"] <= row[name] <= limits["max"]]
            unseen = [name for name, vocabulary in state.get("categories", {}).items()
                      if ("__missing__" if pd.isna(row[name]) else str(row[name])) not in vocabulary]
            ranked.append({"crop_id": row["crop_id"], "display_name": row["display_name"],
                           "crop_group": row["crop_group"], "reference_score": float(scores[index] * 100),
                           "relative_preference": float(preferences[index]),
                           "empirical_reference_error_band": [float(max(0, scores[index] - width) * 100),
                                                               float(min(1, scores[index] + width) * 100)],
                           "missing_features": missing, "outside_training_numeric_range": outside,
                           "unseen_categorical_features": unseen})
        ranked.sort(key=lambda item: (-item["relative_preference"], item["crop_id"]))
        if any(item["outside_training_numeric_range"] for item in ranked):
            warnings.append("Some features exceed development-training ranges; reference extrapolation is unvalidated.")
        if any(item["unseen_categorical_features"] for item in ranked):
            warnings.append("Some categories were absent from training and use an untrained unknown embedding; "
                            "these reference scores need additional review.")
        if len(ranked) == 1:
            warnings.append("A preference of 1 reflects one eligible candidate, not certain agricultural success.")
    return {
        "schema_version": "1", "status": "scored_reference_context" if ranked else "abstained",
        "reason": None if ranked else "no_eligible_trained_candidates", "task": TASK, "method": method,
        "model_id": manifest["model_id"], "dataset_id": manifest["dataset_id"],
        "context": {"context_id": request.context_id, "site_id": context["site_id"],
                    "latitude": float(context["latitude"]), "longitude": float(context["longitude"]),
                    "analysis_start": context["analysis_start"], "analysis_end": context["analysis_end"],
                    "period_id": context["period_id"], "support": "native_5_arcminute_GAEZ_reference_cell",
                    "nasa_support_ids": json.loads(context["nasa_support_ids"]),
                    "source_record_ids": json.loads(context["source_record_ids"])},
        "production_system": request.production_system, "requested_candidates": request.crop_ids,
        "candidate_set": [item["crop_id"] for item in ranked], "ranked": ranked, "withheld": withheld,
        "preference_semantics": "relative_GAEZ_reference_preference_not_probability_of_farming_success",
        "calibration_scope": calibration["candidate_scope"],
        "reference_score_unit": "GAEZ_suitability_index_rescaled_0_to_100",
        "operational_recommendation_ready": False, "rotation_effects_supported": False,
        "unassessed_requirement_axes": manifest["missing_requirement_axes"],
        "attribution": manifest["attribution"],
        "limitations": [
            "Only the saved historical reference cells and complete twenty-year periods are supported.",
            "This is not a next-season planting date, orchard establishment or crop-rotation recommendation.",
            "Removing candidates changes the softmax denominator; subset probabilities are not independently calibrated.",
            "Error bands describe reference-product residuals, not farm-success uncertainty.",
            "Soil groups do not replace local soil tests; use farmer and agricultural-expert review.",
        ],
        "warnings": warnings,
    }


def verify_reference_models(model_path, dataset_path):
    path = Path(model_path)
    manifest = verify_model_bundle(path, "india_reference_models")
    dataset, frame = load_reference_frames(dataset_path)
    require(dataset["dataset_id"] == manifest["dataset_id"], "Wrong evaluation dataset")
    result = {}
    for partition, filename in (("calibration", "calibration_predictions.parquet"), ("test", "test_predictions.parquet")):
        expected = pd.read_parquet(path / filename)
        for method in ("baseline", "catboost", "mlp"):
            predictions = expected[expected.method == method]
            real = frame[frame.partition == partition]
            require(set(predictions.example_id) == set(real.example_id), "Incomplete saved held-out predictions")
            joined = real.merge(predictions[["example_id", "prediction"]], on="example_id", validate="one_to_one")
            model, state = load_estimator(path, method)
            actual = predict_estimator(model, state, joined)
            difference = float(np.abs(actual - joined.prediction.to_numpy()).max())
            require(np.allclose(actual, joined.prediction, rtol=0, atol=1e-7), "Clean model reload prediction mismatch")
            result[f"{partition}:{method}"] = {"rows": len(joined), "maximum_absolute_error": difference}
    return {"status": "verified", "model_id": manifest["model_id"], "replay": result}
