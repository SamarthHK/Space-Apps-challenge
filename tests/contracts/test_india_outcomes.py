"""Authentic district statistics; blank layout cells are not crop observations."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agri_data.contracts.india_cli import database_store
from agri_data.contracts.india_outcomes import build_india_outcomes, normalize_report
from agri_data.contracts.model_records import load_model_records
from agri_data.contracts.outcome_data import checked_bytes, write_json
from agri_data.contracts.source_tables import SourceHTML


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def corpus():
    value = os.environ.get("AGRI_INDIA_OUTCOME_CORPUS")
    assert value, "Set AGRI_INDIA_OUTCOME_CORPUS to an acquired official DES corpus"
    source = json.loads(Path(value).read_bytes())
    assert source["status"] == "complete"
    return source


def test_real_multicrop_report_preserves_values_units_and_aggregate_identity(corpus):
    report = next(item for item in corpus["reports"] if item["selection"]["states"] == ["29"]
                  and item["selection"]["start_year"] <= 2020 <= item["selection"]["end_year"])
    records, evidence = normalize_report(report["asset"], corpus["form"], report["selection"])
    maize = next(row for row in records if row["district_name"] == "Bagalkot"
                 and row["source_crop_id"] == "5" and row["source_season_id"] == "K"
                 and row["reporting_year_start"] == 2020)
    text = checked_bytes(report["asset"]).decode("utf-8")
    assert "61,525.00" in text and "277,170.00" in text
    assert (maize["area"], maize["production"], maize["reported_yield"]) == (61525, 277170, 4.5)
    assert maize["reported_yield_unit"] == "Tonne/Hectare" and maize["arithmetic_status"] == "consistent"
    assert maize["exact_sowing_date"] is maize["historical_available_at"] is maize["boundary_vintage"] is None
    mustard = [row for row in records if row["source_crop_id"] == "17"]
    assert mustard and {row["crop_name"] for row in mustard} == {"Rapeseed &Mustard"}
    assert len(evidence) == 2 * len(records)


def test_empty_report_slots_are_not_manufactured_observations(corpus):
    report = corpus["reports"][0]
    records, _ = normalize_report(report["asset"], corpus["form"], report["selection"])
    grid = SourceHTML(checked_bytes(report["asset"]).decode("utf-8")).table("apyreport").grid()
    displayed_slots = (len(grid) - 3) * ((len(grid[0]) - 3) // 3)
    assert len(records) < displayed_slots
    assert all(any(row[key] is not None for key in ("area", "production", "reported_yield")) for row in records)
    assert len({row["context_id"] for row in records}) == len(records)
    wrong = deepcopy(report["selection"])
    wrong["end_year"] = wrong["start_year"] - 1
    with pytest.raises(ValueError, match="outside requested interval"):
        normalize_report(report["asset"], corpus["form"], wrong)


def test_statistical_records_roundtrip_without_duplicate_sql_rows(corpus, tmp_path):
    selected = deepcopy(corpus)
    selected["reports"] = corpus["reports"][:1]
    selected["assets"] = [corpus["form"], selected["reports"][0]["asset"]]
    selected["selection"] = selected["reports"][0]["selection"]
    source = tmp_path / "selected-corpus.json"
    write_json(source, selected)
    first = build_india_outcomes(source, tmp_path / "first", database_store(ROOT / "config" / "acceptance.yaml"))
    process = subprocess.run(
        [sys.executable, "-m", "agri_data", "build-india-outcomes", "--corpus", str(source),
         "--config", str(ROOT / "config" / "acceptance.yaml"), "--output", str(tmp_path / "second")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    second = json.loads(process.stdout)
    assert first["dataset_id"] == second["dataset_id"] and first["counts"] == second["counts"]
    rows = load_model_records(tmp_path / "second", "regional_outcome")
    assert len(rows) == first["counts"]["regional_outcome"]
    assert all(row["reporting_basis"] == "official_district_aggregate" for row in rows)
