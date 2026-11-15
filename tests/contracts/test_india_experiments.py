"""Numerical preference checks use genuine source scores, not invented crop labels."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agri_data.contracts.india_dataset import load_reference_frames
from agri_data.contracts.india_experiments import finalize_reference_models, masked_softmax


def test_authentic_scores_stay_finite_with_masks_and_extreme_temperature():
    path = os.environ.get("AGRI_INDIA_DATASET")
    assert path, "Set AGRI_INDIA_DATASET to the authentic reference cohort"
    _, frame = load_reference_frames(path)
    frame = frame[frame.partition == "development"]
    row = frame.iloc[0]
    scores = frame[(frame.context_id == row.context_id) & (frame.production_system == row.production_system)].target.to_numpy()
    mask = np.ones(len(scores), dtype=bool)
    mask[0] = False
    values = masked_softmax(scores, mask, 1e-12)
    assert np.isfinite(values).all() and values[0] == 0 and values.sum() == pytest.approx(1)
    assert not masked_softmax(scores, np.zeros(len(scores), dtype=bool), 0.1).any()
    mask[:] = False
    mask[0] = True
    assert masked_softmax(scores, mask, 0.1)[0] == 1
    with pytest.raises(ValueError, match="positive temperature"):
        masked_softmax(scores, mask, 0)


def test_missing_declared_comparisons_cannot_open_the_locked_test(tmp_path):
    dataset = os.environ.get("AGRI_INDIA_DATASET")
    runs = os.environ.get("AGRI_INDIA_CV")
    assert dataset and runs, "Provide the real reference dataset and saved baseline CV run"
    config = Path(__file__).resolve().parents[2] / "config" / "india_model.yaml"
    output = tmp_path / "premature-finalization"
    with pytest.raises(ValueError, match="Complete every predeclared comparison"):
        finalize_reference_models(dataset, config, [Path(runs) / "baseline"], output)
    assert not output.exists()


def test_saved_test_scores_match_independent_error_and_tie_aware_ranking_calculation():
    dataset, models = os.environ.get("AGRI_INDIA_DATASET"), os.environ.get("AGRI_INDIA_MODELS")
    assert dataset and models, "Provide the frozen reference dataset and trained model bundle"
    _, frame = load_reference_frames(dataset)
    held_out = frame[frame.partition == "test"]
    path = Path(models)
    predictions = pd.read_parquet(path / "test_predictions.parquet")
    report = json.loads((path / "report.json").read_bytes())
    for method, recorded in report["models"].items():
        saved = predictions[predictions.method == method][["example_id", "target_record_id", "prediction"]]
        actual = held_out.merge(saved, on=["example_id", "target_record_id"], validate="one_to_one")
        assert len(actual) == len(held_out)
        difference = (actual.prediction - actual.target).to_numpy() * 100
        assert recorded["test"]["mae_index_points"] == pytest.approx(float(np.abs(difference).mean()))
        assert recorded["test"]["rmse_index_points"] == pytest.approx(float(np.sqrt(np.square(difference).mean())))
        ndcg = []
        for _, candidates in actual.groupby(["context_id", "production_system"]):
            if candidates.target.max() == 0:
                continue
            ties = candidates.groupby("prediction").target.agg(["mean", "count"]).sort_index(ascending=False)
            expected_relevance = np.repeat(ties["mean"].to_numpy(), ties["count"].to_numpy())[:5]
            ideal = np.sort(candidates.target.to_numpy())[::-1][:5]
            discount = 1 / np.log2(np.arange(2, len(ideal) + 2))
            ndcg.append(float(np.dot(expected_relevance, discount) / np.dot(ideal, discount)))
        assert len(ndcg) == recorded["test"]["ranked_contexts"]
        assert np.mean(ndcg) == pytest.approx(recorded["test"]["ndcg_at_5"])
