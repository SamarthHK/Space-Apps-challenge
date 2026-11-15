"""Structural checks against the actual plan, not agricultural acceptance evidence."""

from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys

from agri_data.contracts.inventory import extract_inventory
from agri_data.contracts.observation import Observation


ROOT = Path(__file__).resolve().parents[2]


def test_full_plan_inventory_is_preserved_with_unresolved_children():
    inventory = extract_inventory(ROOT / "Plan.md")
    assert inventory["counts"] == {
        "features": 297, "sources": 59, "instruments": 14, "steps": 11, "cases": 68,
    }
    assert inventory["atomic_denominator_frozen"] is False
    lines = (ROOT / "Plan.md").read_text(encoding="utf-8").splitlines()
    for category in ("features", "sources", "instruments", "steps", "cases"):
        for entry in inventory[category]:
            assert lines[entry["plan_line"] - 1].startswith("| " + entry["columns"][0] + " |")
    assert all(feature["owning_steps"] for feature in inventory["features"])
    assert all(feature["expansion_status"] == "blocked" for feature in inventory["features"])


def test_schema_excludes_forbidden_evidence_types_and_tracks_plan_fields():
    schema = Observation.model_json_schema()
    assert schema["additionalProperties"] is False
    evidence_types = set(schema["$defs"]["EvidenceType"]["enum"])
    assert evidence_types == {
        "measured", "surveyed", "published_parameter", "published_recommendation",
        "satellite", "modelled_product", "reanalysis", "projection", "derived",
    }
    for field in (
        "source_binding_id", "raw_sha256", "parent_observation_ids",
        "value_boolean", "value_geometry", "value_series_ref",
        "censoring_qualifier", "detection_limit", "unknown_time_reason",
    ):
        assert field in schema["properties"]


def test_incomplete_acceptance_cli_cannot_report_success():
    result = subprocess.run(
        [sys.executable, "-m", "agri_data", "validate", "--suite", "all",
         "--fresh", "--config", str(ROOT / "config" / "acceptance.yaml")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    output = Path(result.stdout.strip().split("Report: ", 1)[1])
    report = json.loads((output / "validation_report.json").read_text(encoding="utf-8"))
    assert report["overall_complete"] is False
    assert report["scientific_tests_executed"] == 0
    assert report["fresh_requests_executed"] == 0
    assert report["discovery_complete"] is False
    assert report["required_atomic_test_instance_count"] is None
    assert all(not case["executed"] and case["status"] == "blocked" for case in report["case_status"])
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        assert sha256((output / item["path"]).read_bytes()).hexdigest() == item["sha256"]
