"""Real NASA time-window refusal and complete-month aggregation regressions."""

from calendar import monthrange
from copy import deepcopy
from decimal import Decimal
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from agri_data.contracts.india_cli import database_store
from agri_data.contracts.india_environment import build_india_environment, read_monthly
from agri_data.contracts.model_records import load_model_records
from agri_data.contracts.outcome_data import checked_bytes, write_json


ROOT = Path(__file__).resolve().parents[2]


def test_real_api_that_ignores_end_year_cannot_enter_the_requested_window():
    path = os.environ.get("AGRI_NASA_WIDENED_RECEIPT")
    assert path, "Set AGRI_NASA_WIDENED_RECEIPT to the actual mismatched-climatology receipt"
    asset = json.loads(Path(path).read_bytes())
    data = json.loads(checked_bytes(asset))
    assert data["header"]["end"] == "20251231"
    assert "end=2020" in asset["requested_url"]
    with pytest.raises(ValueError, match="no temporal widening"):
        read_monthly(asset, "RH2M", 2001, 2020)


def test_actual_overlapping_monthly_grids_deduplicate_and_do_not_count_annual_rows(tmp_path):
    path = os.environ.get("AGRI_NASA_CORPUS")
    assert path, "Set AGRI_NASA_CORPUS to an acquired monthly corpus"
    corpus = json.loads(Path(path).read_bytes())
    chosen = []
    for report in corpus["reports"]:
        query = parse_qs(urlsplit(report["asset"]["requested_url"]).query)
        if report["parameter"] == "RH2M" and query["longitude-min"] == ["68"] and query["latitude-min"][0] in ("6", "16"):
            chosen.append(report)
    assert len(chosen) == 2
    selected = deepcopy(corpus)
    selected["reports"] = chosen
    selected["assets"] = [report["asset"] for report in chosen]
    selected["specification"]["parameters"] = {"RH2M": ["HP8100", "HP0120"]}
    selected["specification"]["bounds"] = [68, 6, 78, 26]
    source = tmp_path / "subset.json"
    write_json(source, selected)
    first = build_india_environment(source, tmp_path / "first", database_store(ROOT / "config" / "acceptance.yaml"))
    second = build_india_environment(source, tmp_path / "second", database_store(ROOT / "config" / "acceptance.yaml"))
    assert first["dataset_id"] == second["dataset_id"]
    rows = load_model_records(tmp_path / "first", "climate_normal")
    captures = [json.loads(checked_bytes(report["asset"])) for report in chosen]
    assert len(rows) < sum(len(data["features"]) * 2 for data in captures)
    feature = captures[0]["features"][0]
    longitude, latitude = feature["geometry"]["coordinates"][:2]
    monthly = feature["properties"]["parameter"]["RH2M"]
    assert any(key.endswith("13") for key in monthly)
    keys = [f"{year}{month:02d}" for year in range(1981, 2001) for month in range(1, 13)]
    weights = [monthrange(int(key[:4]), int(key[4:]))[1] for key in keys]
    expected = sum(Decimal(str(monthly[key])) * weight for key, weight in zip(keys, weights)) / sum(weights)
    record = next(row for row in rows if row["longitude"] == longitude and row["latitude"] == latitude and row["period_id"] == "HP8100")
    assert record["value"] == pytest.approx(float(expected), abs=1e-12)
    assert record["valid_months"] == record["expected_months"] == 240
