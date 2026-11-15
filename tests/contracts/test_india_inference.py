"""Saved real reference contexts exercise supported inference and closed evidence gates."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
from pydantic import ValidationError
import pytest

from agri_data.contracts.india_inference import ReferenceModel, predict_reference


@pytest.fixture(scope="module")
def artifact():
    value = os.environ.get("AGRI_INDIA_MODELS")
    assert value, "Set AGRI_INDIA_MODELS to the trained authentic reference models"
    path = Path(value)
    return path, json.loads((path / "example_request.json").read_bytes())


def test_saved_real_request_replays_in_a_clean_cli_process(artifact):
    path, request = artifact
    expected = predict_reference(path, request)
    assert expected["status"] == "scored_reference_context"
    assert len(expected["ranked"]) >= 3
    assert sum(row["relative_preference"] for row in expected["ranked"]) == pytest.approx(1)
    process = subprocess.run(
        [sys.executable, "-m", "agri_data", "predict-india-reference", "--models", str(path),
         "--input", str(path / "example_request.json")], capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout) == expected


def test_cached_reference_loader_preserves_scores_and_rejects_a_wrong_model_pin(artifact):
    path, request = artifact
    manifest = json.loads((path / "manifest.json").read_bytes())
    loaded = ReferenceModel(path, manifest["model_id"])
    expected = predict_reference(path, request)
    assert loaded.predict(request) == loaded.predict(request) == expected
    with pytest.raises(ValueError, match="Configured reference model identity differs"):
        ReferenceModel(path, manifest["dataset_id"])


def test_request_schema_import_does_not_require_optional_model_packages():
    script = """
import sys
from agri_data.contracts.india_inference_contract import ReferenceRequest
assert not {'torch', 'catboost', 'psutil', 'pandas', 'agri_data.contracts.india_models'} & set(sys.modules)
assert ReferenceRequest.model_json_schema()['additionalProperties'] is False
"""
    process = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr


def test_known_but_untrained_crop_and_empty_candidate_set_abstain(artifact):
    path, original = artifact
    request = deepcopy(original)
    request["crop_ids"] = ["ecocrop:1112"]
    result = predict_reference(path, request)
    assert result["status"] == "abstained" and not result["ranked"]
    assert result["withheld"][0]["relative_preference"] == 0
    request["crop_ids"] = []
    assert predict_reference(path, request)["status"] == "abstained"
    request["crop_ids"] = original["crop_ids"]
    request["excluded_crop_ids"] = original["crop_ids"][1:]
    result = predict_reference(path, request)
    assert len(result["ranked"]) == 1 and result["ranked"][0]["relative_preference"] == 1


def test_actual_reference_cannot_be_relabelled_as_a_season_or_rotation(artifact):
    path, original = artifact
    request = deepcopy(original)
    request["analysis_start"] = request["analysis_end"]
    with pytest.raises(ValueError, match="interval differs"):
        predict_reference(path, request)
    request = deepcopy(original)
    request["mode"] = "strict_as_of_recommendation"
    with pytest.raises(ValidationError):
        predict_reference(path, request)
    request = deepcopy(original)
    request["task"] = "field_rotation_outcomes"
    with pytest.raises(ValidationError):
        predict_reference(path, request)
    request = deepcopy(original)
    request["crop_ids"].append(request["crop_ids"][0])
    with pytest.raises(ValidationError, match="Repeated candidates"):
        predict_reference(path, request)


def test_real_unseen_soil_group_is_explicitly_qualified_without_changing_the_model(artifact):
    path, original = artifact
    state = json.loads((path / "mlp.state.json").read_bytes())
    contexts = pd.read_parquet(path / "contexts.parquet")
    unknown = contexts[~contexts["static_HWSDV201"].isin(state["categories"]["static_HWSDV201"])]
    assert not unknown.empty, "Use an actual soil class absent from the fitted training vocabulary"
    row = unknown.iloc[0]
    request = {**original, "context_id": row.context_id,
               "analysis_start": row.analysis_start, "analysis_end": row.analysis_end}
    result = predict_reference(path, request)
    assert result["method"] == "mlp" and result["ranked"]
    assert all("static_HWSDV201" in candidate["unseen_categorical_features"] for candidate in result["ranked"])
    assert any("untrained unknown embedding" in warning for warning in result["warnings"])
