"""Bounded fits and clean-process replay use only actual development observations."""

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from agri_data.contracts.india_dataset import load_reference_frames
from agri_data.contracts.india_models import _neural_arrays, fit_admitted, predict_estimator, reference_metrics, save_estimator
from agri_data.contracts.model_resources import admit, snapshot


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def development():
    path = os.environ.get("AGRI_INDIA_DATASET")
    assert path, "Set AGRI_INDIA_DATASET to the authentic reference training cohort"
    manifest, frame = load_reference_frames(path)
    frame = frame[(frame.partition == "development") & frame.crop_id.isin(["gaez:MZE", "gaez:WHE", "gaez:GRD"])]
    return manifest, frame[frame.fold != 0].copy(), frame[frame.fold == 0].copy()


@pytest.mark.parametrize("method", ["baseline", "catboost", "mlp"])
def test_real_development_fit_and_separate_process_reload(development, method, tmp_path):
    manifest, train, validation = development
    parameters = {"seed": 20261115, "iterations": 30, "depth": 4, "learning_rate": 0.01 if method == "mlp" else 0.1,
                  "l2_leaf_reg": 5, "epochs": 3, "batch_size": 1024, "hidden": 64,
                  "dropout": 0.1, "weight_decay": 0.0001, "patience": 2}
    model, state = fit_admitted(train, validation, manifest["features"], method, parameters)
    prediction = predict_estimator(model, state, validation)
    assert np.isfinite(prediction).all() and ((prediction >= 0) & (prediction <= 1)).all()
    assert reference_metrics(validation, prediction)["mae_index_points"] == pytest.approx(
        np.abs(prediction - validation.target.to_numpy()).mean() * 100)
    assert not state["resource_telemetry"]["training"]["reserve_breached"]
    save_estimator(model, state, tmp_path, "candidate")
    sample = validation.iloc[:19]
    sample.to_parquet(tmp_path / "real-examples.parquet", index=False)
    script = """
import json, pathlib, sys
import pandas as pd
from agri_data.contracts.india_models import load_estimator, predict_estimator
p=pathlib.Path(sys.argv[1])
model,state=load_estimator(p,'candidate')
print(json.dumps(predict_estimator(model,state,pd.read_parquet(p/'real-examples.parquet')).tolist()))
"""
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    assert np.allclose(json.loads(process.stdout), predict_estimator(model, state, sample), atol=1e-7)
    if method == "mlp":
        assert "nasa_ALLSKY_SFC_SW_DWN" in state["numeric"]
        assert state["missing_representation"].endswith("not_stored_imputation")
        numeric, _ = _neural_arrays(validation, state)
        column = state["numeric"].index("nasa_ALLSKY_SFC_SW_DWN")
        absent = validation["nasa_ALLSKY_SFC_SW_DWN"].isna().to_numpy()
        assert absent.any()
        assert (numeric[absent, column] == 0).all()
        assert (numeric[:, column + len(state["numeric"])] == ~absent).all()


def test_measured_machine_capacity_refuses_an_oversized_owned_job():
    measured = snapshot()
    with pytest.raises(ValueError, match="Insufficient free RAM"):
        admit(measured["available_ram_bytes"], measured)
