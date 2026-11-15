import json
import pytest
from agri_data.sources.imports import load_import_plan, import_dataset
from agri_data.geo.kml import load_kml


def test_import_preserves_text_missing_depth_and_original_bytes(tmp_path, monkeypatch):
    from agri_data.config import settings
    monkeypatch.setattr(settings, "raw_dir", tmp_path / "raw")
    payload = [{"variable_id": "aquifer", "value_text": "granite", "observed_at": "2025-01-01"},
               {"variable_id": "aquifer", "value_numeric": None, "missing_reason": "NOT_COLLECTED"}]
    path = tmp_path / "samples.json"
    path.write_text(json.dumps(payload))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"datasets": [{"id": "wells", "source_id": "local_wells", "domain": "water", "field_name": "test", "path": "samples.json", "variables": {"aquifer": {"unit": "category", "description": "Aquifer formation"}}}]}))
    dataset = load_import_plan(plan)[0]
    result = import_dataset(dataset, load_kml("data/input/farm_area.kml").iloc[0])
    from pathlib import Path
    assert Path(result["raw_file"]).read_bytes() == path.read_bytes()
    assert len(result["observations"]) == 2
    assert result["observations"][0]["value_text"] == "granite"
    assert result["observations"][1]["quality_flag"] == "MISSING"


def test_import_rejects_nonfinite_values(tmp_path):
    path = tmp_path / "samples.json"
    path.write_text('[{"variable_id":"soil_ph","value_numeric":"nan"}]')
    dataset = {"path": str(path), "variables": {"soil_ph": {"unit": "pH"}}, "source_id": "lab", "domain": "soil", "id": "lab"}
    with pytest.raises(ValueError, match="non-finite"):
        import_dataset(dataset, load_kml("data/input/farm_area.kml").iloc[0])
