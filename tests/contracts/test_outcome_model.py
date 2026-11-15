"""Real-source modeling tests; configure AGRI_OUTCOME_DATASET after acquisition."""

from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
import pandas as pd
import pytest
import yaml

from agri_data.contracts.outcome_data import build_outcome_dataset, read_broadbalk
from agri_data.contracts.outcome_model import (
    assemble_features, assign_splits, predict_example, train_outcomes, verify_bundle, weather_features,
)
from agri_data.contracts.postgres import PostgresStore


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def dataset():
    path = os.environ.get("AGRI_OUTCOME_DATASET")
    assert path, "Set AGRI_OUTCOME_DATASET to an authentic build-outcomes bundle"
    path = Path(path).resolve()
    verify_bundle(path)
    return path


@pytest.fixture(scope="module")
def assembled(dataset):
    return assemble_features(dataset)


@pytest.fixture(scope="module")
def trained(dataset):
    output = ROOT / "data" / "exports" / ("model-regression-" + uuid.uuid4().hex)
    report = train_outcomes(dataset, output)
    return output, report


def test_authentic_source_units_aliases_and_idempotent_database(dataset):
    config = yaml.safe_load((ROOT / "config" / "acceptance.yaml").read_bytes())["database"]
    store = PostgresStore(config["expected_database"], config["expected_user"], config["acceptance_schema"],
                          config["connection_environment_variable"])
    old = verify_bundle(dataset)
    output = ROOT / "data" / "exports" / ("outcome-replay-" + uuid.uuid4().hex)
    replay = build_outcome_dataset(dataset / "corpus.json", output, store)
    assert old["dataset_id"] == replay["dataset_id"]
    assert old["counts"] == replay["counts"]
    corpus = json.loads((dataset / "corpus.json").read_bytes())
    aliased = []
    for entry in corpus["sources"]:
        rows, _ = read_broadbalk(entry)
        for row in rows:
            raw = row["raw_record"][entry["spec"]["target_column"]]
            if row["yield_kg_ha"] is not None:
                assert row["yield_kg_ha"] == pytest.approx(float(raw) * 1000)
            if row["original_plot_id"].startswith(("2.1\\", "2.2\\")):
                aliased.append(row)
                assert row["plot_id"].startswith(("21\\", "22\\"))
    assert aliased, "Use actual source plot aliases, not generated fixtures"
    with store.session() as connection:
        count = connection.execute("SELECT count(*) FROM model_dataset_records WHERE dataset_id=%s",
                                   (old["dataset_id"],)).fetchone()[0]
    assert count == sum(old["counts"][name] for name in ("outcomes", "weather_days"))


def test_features_use_only_preplant_records_and_preserve_missing_data(dataset, assembled):
    frame, features, excluded, config, _ = assembled
    assert not frame["context_id"].duplicated().any()
    assert (frame["cutoff"] < frame["sowing_date"]).all()
    assert not set(features) & {"yield_kg_ha", "harvest_date", "harvest_year", "plot_id", "record_id", "group_id"}
    assert not any(name.endswith("_coverage") for name in features)
    assert not any("daily_rainfall_mean" in name for name in features)
    assert excluded and frame[features].isna().any().any()
    weather = pd.read_parquet(dataset / "weather.parquet")
    actual = frame.iloc[0]
    days = weather.loc[weather["site_id"] == actual.site_id].copy()
    days.index = pd.to_datetime(days["date"])
    days = days.sort_index()
    cutoff = date.fromisoformat(actual.cutoff)
    args = (cutoff, config["weather"]["windows_days"], config["weather"]["minimum_coverage"])
    assert weather_features(days, *args) == weather_features(days.loc[:actual.cutoff], *args)
    independently = days.loc[pd.Timestamp(cutoff) - pd.Timedelta(days=29):actual.cutoff, "daily_rainfall"]
    assert actual.w30_rainfall_total_mm == pytest.approx(independently.sum())
    outcomes = pd.read_parquet(dataset / "outcomes.parquet").set_index("record_id")
    for item in frame.loc[frame["p_preplant_kg_ha"].notna()].itertuples():
        raw = json.loads(outcomes.loc[item.record_id, "raw_record"])
        assert raw["p_date"][:10] <= item.cutoff
        assert item.p_preplant_kg_ha == float(raw["p_amount"])


def test_splits_separate_main_plots_and_outcome_availability(assembled):
    frame, _, _, config, _ = assembled
    checked = 0
    for _, crop in frame.groupby("crop_id"):
        try:
            split = assign_splits(crop, config["evaluation"])
        except ValueError:
            continue
        groups = {}
        for name in ("train", "validation", "test"):
            part = split.loc[split["split"] == name]
            groups[name] = set(part["group_id"])
            assert len(part) > 0
        assert groups["train"].isdisjoint(groups["validation"] | groups["test"])
        assert groups["validation"].isdisjoint(groups["test"])
        for early, late in (("train", "validation"), ("validation", "test")):
            assert split.loc[split["split"] == early, "harvest_date"].max() < split.loc[
                split["split"] == late, "cutoff"].min()
        checked += 1
    assert checked > 1


def test_real_training_reload_metrics_and_unsupported_inputs(trained):
    output, report = trained
    verify_bundle(output)
    examples = pd.read_parquet(output / "examples.parquet")
    predictions = pd.read_parquet(output / "test_predictions.parquet")
    models = {name: model for name, model in report["models"].items() if model["status"] == "trained"}
    assert len(models) > 1 and report["operational_recommendation_ready"] is False
    for crop, model in models.items():
        expected = examples[(examples.crop_id == crop) & (examples.split == "test")].set_index("record_id")
        predicted = predictions[(predictions.crop_id == crop) & (predictions.method == "selected")].set_index("record_id")
        error = expected.yield_kg_ha - predicted.predicted_yield_kg_ha
        assert np.isfinite(error).all()
        assert np.abs(error).mean() == pytest.approx(model["test_selected"]["mae_kg_ha"])
        source = output / f"{crop}.input.json"
        sample = json.loads(source.read_bytes())
        first = predict_example(output, sample)
        process = subprocess.run(
            [sys.executable, "-m", "agri_data", "predict-outcome", "--model", str(output), "--input", str(source)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert process.returncode == 0, process.stderr
        assert first == json.loads(process.stdout)
        incomplete = {key: value for key, value in sample.items() if key != model["features"][0]}
        with pytest.raises(ValueError, match="Missing required"):
            predict_example(output, incomplete)
    # A real crop present in the corpus but without enough training rows must
    # not acquire a prediction merely because a different crop trained.
    unsupported = [name for name, model in report["models"].items() if model["status"] != "trained"]
    for crop in unsupported:
        with pytest.raises(ValueError, match="Unsupported crop"):
            predict_example(output, {"crop_id": crop})
