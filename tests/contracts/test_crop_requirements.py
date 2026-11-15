"""Regression checks against acquired EcoCrop pages and real PostgreSQL."""

from copy import deepcopy
from decimal import Decimal
from html import unescape
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from agri_data.contracts.crop_requirements import build_crop_profiles, normalize_crop_profiles
from agri_data.contracts.india_cli import database_store
from agri_data.contracts.model_records import load_model_records, verify_model_bundle
from agri_data.contracts.outcome_data import checked_bytes


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def corpus():
    value = os.environ.get("AGRI_INDIA_PROFILE_CORPUS")
    assert value, "Set AGRI_INDIA_PROFILE_CORPUS to an acquired crop-profile corpus"
    path = Path(value).resolve()
    source = json.loads(path.read_bytes())
    assert source["status"] == "complete"
    return path, source


def test_numeric_ranges_are_from_correct_source_cells_with_explicit_support(corpus):
    records, evidence = normalize_crop_profiles(corpus[1])
    requirements = {(row["source_crop_id"], row["metric_id"]): row
                    for row in records if row["record_kind"] == "crop_requirement"}
    fields = {"Temperat. requir.": "temperature", "Rainfall (annual)": "annual_water", "Soil PH": "soil_ph"}
    for identifier, asset in corpus[1]["profiles"].items():
        text = checked_bytes(asset).decode("utf-8")
        for label, metric in fields.items():
            raw = re.search(r"<tr>\s*<th>" + re.escape(label) + r"</th>(.*?)</tr>", text, re.S)[1]
            expected = [Decimal(unescape(value).strip()) for value in re.findall(r"<td>(.*?)</td>", raw, re.S)[:4]]
            row = requirements[identifier, metric]
            assert [Decimal(str(row[key])) for key in ("optimal_min", "optimal_max", "absolute_min", "absolute_max")] == expected
            assert any(proof["record_id"] == row["record_id"] and proof["evidence_role"] == "definition"
                       for proof in evidence)
        assert requirements[identifier, "annual_water"]["temporal_support"] == "annual"
        assert requirements[identifier, "temperature"]["temporal_support"] == "growing_season"
    assert len(requirements) > len(corpus[1]["profiles"]) * len(fields)


def test_real_gaps_and_perennial_cycle_ambiguity_do_not_become_filled_values(corpus):
    records, _ = normalize_crop_profiles(corpus[1])
    rows = {(row["source_crop_id"], row.get("metric_id")): row for row in records}
    maize = rows["2175", "soil_texture"]
    assert maize["availability"] == "missing"
    assert set(maize["categories"].values()) == {None}
    mung = rows["2150", "biological_life_span"]
    assert mung["value_text"] == "perennial" and mung["limitation"]
    mango = rows["1416", "crop_cycle"]
    assert mango["minimum"] == 150 and mango["maximum"] == 365
    assert mango["temporal_support"] == "source_cycle" and mango["limitation"]
    assert mango["optimal_min"] is None and mango["absolute_min"] is None
    assert rows["1416", "latitude"]["availability"] == "unresolved"
    assert all(row["evidence_type"] == "published_parameter" for row in records)


def test_misbound_real_crop_profile_is_rejected(corpus):
    wrong = deepcopy(corpus[1])
    wrong["profiles"]["1574"] = wrong["profiles"]["2114"]
    with pytest.raises(ValueError, match="identifier mismatch"):
        normalize_crop_profiles(wrong)


def test_real_database_repeat_import_and_independent_process_export(corpus, tmp_path):
    store = database_store(ROOT / "config" / "acceptance.yaml")
    first = build_crop_profiles(corpus[0], tmp_path / "first", store)
    process = subprocess.run(
        [sys.executable, "-m", "agri_data", "build-crop-profiles", "--corpus", str(corpus[0]),
         "--config", str(ROOT / "config" / "acceptance.yaml"), "--output", str(tmp_path / "second")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    second = json.loads(process.stdout)
    assert first["dataset_id"] == second["dataset_id"]
    assert first["counts"] == second["counts"]
    for path in (tmp_path / "first", tmp_path / "second"):
        manifest = verify_model_bundle(path, "crop_requirement_dataset")
        assert manifest["contract"]["india_presence_verified"] is False
        assert manifest["contract"]["observed_outcome_labels"] is False
        restored = load_model_records(path, "crop_requirement")
        assert len({row["context_id"] for row in restored}) == len(restored)
    with store.session() as connection:
        counts = connection.execute(
            "SELECT count(*) FROM model_dataset_records WHERE dataset_id=%s", (first["dataset_id"],),
        ).fetchone()[0]
        linked = connection.execute(
            "SELECT count(DISTINCT record_id) FROM model_record_evidence WHERE dataset_id=%s",
            (first["dataset_id"],),
        ).fetchone()[0]
    assert counts == linked == sum(first["counts"].values())
