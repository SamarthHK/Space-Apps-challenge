"""Retrospective, time-bounded crop outcome learning, not causal optimization."""

from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .identity import fingerprint
from .outcome_data import write_json, number, source_date
from .storage_proof import require


CATEGORICAL = ["site_id", "crop_form", "previous_crop", "cultivar", "rotation_code"]
PREPLANT_EVENTS = {
    "p_preplant_kg_ha": ("p_amount", "p_date"),
    "k_preplant_kg_ha": ("k_amount", "k_date"),
    "mg_preplant_kg_ha": ("mg_amount", "mg_date"),
    "fym_preplant_t_ha": ("fym_applied", "fym_date"),
    "n_autumn_preplant_kg_ha": ("autumn_n_kg/ha", "autumn_n_date"),
}
WEATHER_VARIABLES = [
    "daily_rainfall", "temperature_mean", "temperature_max", "temperature_min",
    "relative_humidity", "wind_speed", "solar_radiation",
]


def verify_bundle(path):
    manifest = json.loads((path / "manifest.json").read_bytes())
    for name, digest in manifest["files"].items():
        file = (path / name).resolve()
        require(file.parent == path.resolve(), "Invalid bundle path")
        require(sha256(file.read_bytes()).hexdigest() == digest, "Bundle checksum mismatch")
    return manifest


def weather_features(weather, cutoff, windows, minimum_coverage):
    """Use only observed days at/before cutoff; incomplete sums stay missing."""
    result = {}
    for window in windows:
        dates = pd.date_range(cutoff - timedelta(days=window - 1), cutoff)
        selected = weather.reindex(dates)
        prefix = f"w{window}_"
        for variable in WEATHER_VARIABLES:
            series = selected[variable]
            coverage = float(series.notna().mean())
            result[prefix + variable + "_coverage"] = coverage
            if variable != "daily_rainfall":
                result[prefix + variable + "_mean"] = (
                    float(series.mean()) if coverage >= minimum_coverage else None)
        rainfall = selected["daily_rainfall"]
        result[prefix + "rainfall_total_mm"] = float(rainfall.sum()) if rainfall.notna().all() else None
        result[prefix + "wet_days_ge_1mm"] = int((rainfall >= 1).sum()) if rainfall.notna().all() else None
        longest = current = 0
        for value in rainfall:
            current = current + 1 if pd.notna(value) and value < 1 else 0
            longest = max(longest, current)
        result[prefix + "longest_dry_spell_lt_1mm"] = longest if rainfall.notna().all() else None
        mean = selected["temperature_mean"]
        result[prefix + "temperature_std_c"] = (
            float(mean.std(ddof=0)) if mean.notna().mean() >= minimum_coverage else None)
        for variable, label, threshold, above in (
            ("temperature_min", "days_below_0c", 0, False),
            ("temperature_max", "days_above_30c", 30, True),
        ):
            values = selected[variable]
            result[prefix + label] = (int(((values > threshold) if above else (values < threshold)).sum())
                                      if values.notna().all() else None)
    return result


def assemble_features(dataset):
    manifest = verify_bundle(dataset)
    require(manifest["kind"] == "retrospective_outcome_dataset", "Wrong dataset kind")
    corpus = json.loads((dataset / "corpus.json").read_bytes())
    config = corpus["config"]
    outcomes = pd.read_parquet(dataset / "outcomes.parquet")
    weather = pd.read_parquet(dataset / "weather.parquet")
    frames = {}
    for site, rows in weather.groupby("site_id"):
        require(not rows["date"].duplicated().any(), "Duplicate site/day weather")
        rows = rows.copy()
        rows.index = pd.to_datetime(rows["date"])
        frames[site] = rows
    examples, exclusions, cache = [], [], {}
    for row in outcomes.to_dict("records"):
        reasons = []
        sowing, harvest = source_date(row["sowing_date"]), source_date(row["harvest_date"])
        target = number(row["yield_kg_ha"])
        if target is None or target < 0:
            reasons.append("missing_or_invalid_yield")
        if "fallow" in str(row["crop_form"]).lower():
            reasons.append("no_crop")
        if sowing is None or harvest is None or (sowing and harvest and harvest < sowing):
            reasons.append("missing_or_invalid_crop_dates")
        # These source notes explicitly question or estimate the response itself.
        if row["crop_id"] == "oats" and row["harvest_year"] == 2012 and row["plot_id"].startswith("1\\"):
            reasons.append("source_estimated_grain_yield")
        if row["crop_id"] == "field_beans" and row["harvest_year"] == 2021 and row["plot_id"] == "15\\5":
            reasons.append("source_questions_grain_sample")
        if row["site_id"] == "woburn" and row["harvest_year"] == 2015:
            reasons.append("replacement_crop_after_winter_crop_failure")
        if reasons:
            exclusions.append({"record_id": row["record_id"], "reasons": reasons})
            continue
        cutoff = date.fromisoformat(sowing) - timedelta(days=1)
        frame = frames[row["site_id"]]
        if (pd.Timestamp(cutoff - timedelta(days=max(config["weather"]["windows_days"]) - 1)) < frame.index.min()
                or pd.Timestamp(cutoff) > frame.index.max()):
            exclusions.append({"record_id": row["record_id"], "reasons": ["outside_weather_period"]})
            continue
        key = (row["site_id"], cutoff)
        if key not in cache:
            cache[key] = weather_features(frame, cutoff, config["weather"]["windows_days"],
                                          config["weather"]["minimum_coverage"])
        item = {name: str(row[name]) if pd.notna(row[name]) else "__missing__" for name in CATEGORICAL}
        item.update(cache[key])
        raw = json.loads(row["raw_record"])
        for name, (amount_field, date_field) in PREPLANT_EVENTS.items():
            amount, event_date = number(raw.get(amount_field)), source_date(raw.get(date_field))
            item[name] = amount if (event_date and event_date <= cutoff.isoformat()) else None
        day = date.fromisoformat(sowing).timetuple().tm_yday
        item.update(sowing_day_sin=math.sin(2 * math.pi * day / 365.25),
                    sowing_day_cos=math.cos(2 * math.pi * day / 365.25))
        item.update({
            "record_id": row["record_id"], "crop_id": row["crop_id"], "plot_id": row["plot_id"],
            "group_id": row["group_id"],
            "context_id": row["context_id"], "cutoff": cutoff.isoformat(), "sowing_date": sowing,
            "harvest_date": harvest, "harvest_year": row["harvest_year"], "yield_kg_ha": target,
            "mass_basis": row["mass_basis"], "source_asset_id": row["source_asset_id"],
            "weather_asset_id": corpus["weather"][row["site_id"]]["raw_sha256"],
        })
        examples.append(item)
    frame = pd.DataFrame(examples)
    require(not frame.empty and not frame["context_id"].duplicated().any(), "No unique crop-season examples")
    metadata = {
        "record_id", "crop_id", "plot_id", "group_id", "context_id", "cutoff", "sowing_date",
        "harvest_date", "harvest_year", "yield_kg_ha", "mass_basis", "source_asset_id", "weather_asset_id",
    }
    features = [name for name in frame.columns if name not in metadata and not name.endswith("_coverage")]
    return frame, features, exclusions, config, manifest


def assign_splits(frame, settings):
    """Hold out whole plots as well as later seasons; unused rows stay explicit."""
    result = frame.copy()
    years = sorted(result["harvest_year"].unique())
    require(len(years) >= settings["minimum_years"], "Insufficient harvest-year groups")
    first = max(1, int(len(years) * settings["train_fraction"]))
    second = min(len(years) - 1, max(first + 1, int(len(years) * (
        settings["train_fraction"] + settings["validation_fraction"]))))
    require(first < second < len(years), "Invalid split fractions")
    groups = result["group_id"].map(lambda value: int(value[:8], 16) % 5)
    result["split"] = "withheld"
    result.loc[(result["harvest_year"] < years[first]) & (groups >= 2), "split"] = "train"
    result.loc[(result["harvest_year"] >= years[first]) & (result["harvest_year"] < years[second])
               & (groups == 1), "split"] = "validation"
    result.loc[(result["harvest_year"] >= years[second]) & (groups == 0), "split"] = "test"
    for early, late in (("validation", "test"), ("train", "validation")):
        later = result.loc[result["split"] == late]
        require(not later.empty, f"Empty {late} partition")
        cutoff = later["cutoff"].min()
        result.loc[(result["split"] == early) & (result["harvest_date"] >= cutoff), "split"] = "withheld"
    require((result["split"] == "train").sum() >= settings["minimum_training_rows"], "Insufficient training rows")
    for split in ("train", "validation", "test"):
        require((result["split"] == split).any(), f"No {split} rows")
    result["split_reason"] = result["split"].map({
        "train": "earlier_seasons_training_main_plots",
        "validation": "later_seasons_distinct_main_plots",
        "test": "latest_seasons_distinct_main_plots",
        "withheld": "group_time_reservation_or_temporal_embargo",
    })
    return result


def metrics(actual, predicted):
    error = np.asarray(actual) - np.asarray(predicted)
    return {"rows": len(error), "mae_kg_ha": float(np.abs(error).mean()),
            "rmse_kg_ha": float(np.sqrt((error ** 2).mean()))}


def baseline_fit(train):
    groups = train.groupby(["site_id", "previous_crop", "rotation_code"])["yield_kg_ha"].mean()
    return {"mean": float(train["yield_kg_ha"].mean()),
            "groups": {json.dumps(list(key)): float(value) for key, value in groups.items()}}


def baseline_predict(model, frame):
    return np.array([model["groups"].get(json.dumps([row[name] for name in (
        "site_id", "previous_crop", "rotation_code")]), model["mean"])
        for row in frame.to_dict("records")])


def model_inputs(frame, features):
    result = frame[features].copy()
    for name in features:
        if name in CATEGORICAL:
            result[name] = result[name].fillna("__missing__").astype(str)
        else:
            result[name] = pd.to_numeric(result[name], errors="raise").astype(float)
    return result


def train_outcomes(dataset, output):
    from catboost import CatBoostRegressor
    import catboost
    output.mkdir(parents=True, exist_ok=False)
    try:
        frame, features, exclusions, config, source_manifest = assemble_features(dataset)
        settings = config["evaluation"]
        reports, predictions, partitions = {}, [], []
        for crop, rows in frame.groupby("crop_id"):
            try:
                split = assign_splits(rows, settings)
            except ValueError as error:
                reports[crop] = {"status": "insufficient_data", "reason": str(error), "rows": len(rows)}
                partitions.append(rows.assign(split="withheld", split_reason=str(error)))
                continue
            train = split.loc[split["split"] == "train"]
            validation = split.loc[split["split"] == "validation"]
            test = split.loc[split["split"] == "test"]
            require(len(set(rows["mass_basis"])) == 1, "Mixed target mass bases")
            crop_features = [name for name in features if train[name].nunique(dropna=False) > 1]
            require(bool(crop_features), "No varying training predictors")
            baseline = baseline_fit(train)
            model = CatBoostRegressor(
                iterations=settings["iterations"], depth=settings["depth"],
                learning_rate=settings["learning_rate"], random_seed=settings["seed"],
                loss_function="RMSE", thread_count=settings["threads"],
                allow_writing_files=False, verbose=False,
            )
            model.fit(model_inputs(train, crop_features), train["yield_kg_ha"],
                      cat_features=[name for name in CATEGORICAL if name in crop_features])
            val_model = model.predict(model_inputs(validation, crop_features))
            val_base = baseline_predict(baseline, validation)
            selected = ("catboost" if metrics(validation["yield_kg_ha"], val_model)["mae_kg_ha"]
                        < metrics(validation["yield_kg_ha"], val_base)["mae_kg_ha"] else "baseline")
            val_selected = val_model if selected == "catboost" else val_base
            width = float(np.quantile(np.abs(validation["yield_kg_ha"].to_numpy() - val_selected), 0.9))
            test_model = model.predict(model_inputs(test, crop_features))
            test_base = baseline_predict(baseline, test)
            selected_prediction = test_model if selected == "catboost" else test_base
            nonweather = [name for name in crop_features if not name.startswith("w")]
            ablation = CatBoostRegressor(**model.get_params())
            ablation.fit(model_inputs(train, nonweather), train["yield_kg_ha"],
                         cat_features=[name for name in CATEGORICAL if name in nonweather])
            ablation_prediction = ablation.predict(model_inputs(test, nonweather))
            model.save_model(str(output / f"{crop}.cbm"))
            write_json(output / f"{crop}.baseline.json", baseline)
            sample = train.iloc[0][["crop_id"] + features]
            write_json(output / f"{crop}.input.json", json.loads(sample.to_json()))
            for name, values in (("catboost", test_model), ("baseline", test_base),
                                 ("selected", selected_prediction), ("without_weather", ablation_prediction)):
                for record, value in zip(test["record_id"], values):
                    predictions.append({"record_id": record, "crop_id": crop, "method": name,
                                        "predicted_yield_kg_ha": float(value)})
            partitions.append(split)
            support = {name: sorted(train[name].unique().tolist()) for name in CATEGORICAL}
            reports[crop] = {
                "status": "trained", "selected_method": selected,
                "features": crop_features,
                "validation_catboost": metrics(validation["yield_kg_ha"], val_model),
                "validation_baseline": metrics(validation["yield_kg_ha"], val_base),
                "partition_rows": split["split"].value_counts().to_dict(),
                "partition_years": {name: sorted(map(int, split.loc[split["split"] == name, "harvest_year"].unique()))
                                    for name in ("train", "validation", "test")},
                "mass_basis": rows["mass_basis"].iloc[0], "target_unit": "kg/ha",
                "test_catboost": metrics(test["yield_kg_ha"], test_model),
                "test_baseline": metrics(test["yield_kg_ha"], test_base),
                "test_selected": metrics(test["yield_kg_ha"], selected_prediction),
                "test_without_weather": metrics(test["yield_kg_ha"], ablation_prediction),
                "validation_residual_90pct_kg_ha": width,
                "test_empirical_interval_coverage": float(
                    (np.abs(test["yield_kg_ha"].to_numpy() - selected_prediction) <= width).mean()),
                "categorical_support": support,
                "numeric_support": {name: {"min": float(train[name].min()), "max": float(train[name].max())}
                                    for name in crop_features if name not in CATEGORICAL and train[name].notna().any()},
                "feature_importance": dict(sorted(zip(crop_features, map(float, model.feature_importances_)),
                                                 key=lambda item: -item[1])),
            }
        require(any(model["status"] == "trained" for model in reports.values()),
                "No crop model has sufficient training/evaluation data")
        pd.concat(partitions).to_parquet(output / "examples.parquet", index=False)
        pd.DataFrame(predictions).to_parquet(output / "test_predictions.parquet", index=False)
        write_json(output / "exclusions.json", exclusions)
        write_json(output / "features.json", {
            "columns": features, "categorical": CATEGORICAL,
            "weather_units": {"daily_rainfall": "mm/day", "temperature_mean": "C",
                              "temperature_min": "C", "temperature_max": "C", "relative_humidity": "%",
                              "wind_speed": "m/s", "solar_radiation": "MJ/m^2/day"},
            "preplant_events": PREPLANT_EVENTS, "config": config,
        })
        report = {
            "status": "research_models_trained", "operational_recommendation_ready": False,
            "candidate_rows": len(frame), "excluded_rows": len(exclusions), "feature_count": len(features),
            "models": reports, "dataset_id": source_manifest["dataset_id"],
            "citations": source_manifest["citations"], "attribution": source_manifest["attribution"],
            "acknowledgement": source_manifest["acknowledgement"],
            "limitations": [
                "Retrospective reconstruction using reanalysis and published records, not archived decision-time forecasts.",
                "Two English experimental locations do not establish geographic or commercial-farm generalization.",
                "Whole Broadbalk strips/Woburn main plots and later seasons are held out within each crop.",
                "Crop models have different cutoff years; this is not one shared-date multicrop backtest.",
                "Target units/mass bases differ; raw yields must not be used for cross-crop ranking.",
                "Rotation associations are not causal treatment effects; no soil transition model is fitted.",
                "Intervals are empirical validation residual bands, not guaranteed coverage probabilities.",
                "Missing soil and unknown prior crops remain missing; no generated agricultural data or imputation.",
                "Scientific pending status does not prevent this explicitly labeled engineering/research experiment.",
            ],
        }
        write_json(output / "report.json", report)
        manifest = {
            "kind": "retrospective_outcome_models", "dataset_id": source_manifest["dataset_id"],
            "catboost_version": catboost.__version__,
            "dataset_manifest_sha256": sha256((dataset / "manifest.json").read_bytes()).hexdigest(),
            "lock_sha256": sha256((Path.cwd() / "uv.lock").read_bytes()).hexdigest(),
            "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
            "code": {p.name: sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
        }
        write_json(output / "manifest.json", manifest)
        return report
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise


def predict_example(model_path, example):
    """Predict one fully assembled supported context; never rank unlike crop yields."""
    from catboost import CatBoostRegressor
    verify_bundle(model_path)
    report = json.loads((model_path / "report.json").read_bytes())
    definition = json.loads((model_path / "features.json").read_bytes())
    crop = example["crop_id"]
    require(crop in report["models"] and report["models"][crop]["status"] == "trained", "Unsupported crop")
    summary = report["models"][crop]
    required = set(summary["features"]) | set(CATEGORICAL)
    require(required <= set(example), "Missing required feature columns")
    for name, values in summary["categorical_support"].items():
        require(example[name] in values, f"Unsupported {name}")
    for name, limits in summary["numeric_support"].items():
        value = example[name]
        if value is not None:
            value = float(value)
            require(math.isfinite(value) and
                    (value >= limits["min"] or math.isclose(value, limits["min"], abs_tol=1e-12)) and
                    (value <= limits["max"] or math.isclose(value, limits["max"], abs_tol=1e-12)),
                    f"Outside training range: {name}")
    frame = pd.DataFrame([example])
    if summary["selected_method"] == "catboost":
        model = CatBoostRegressor()
        model.load_model(str(model_path / f"{crop}.cbm"))
        value = float(model.predict(model_inputs(frame, summary["features"]))[0])
    else:
        baseline = json.loads((model_path / f"{crop}.baseline.json").read_bytes())
        value = float(baseline_predict(baseline, frame)[0])
    width = summary["validation_residual_90pct_kg_ha"]
    return {"crop_id": crop, "predicted_yield_kg_ha": value, "mass_basis": summary["mass_basis"],
            "empirical_residual_band_kg_ha": [value - width, value + width],
            "method": summary["selected_method"], "operational_recommendation_ready": False}
