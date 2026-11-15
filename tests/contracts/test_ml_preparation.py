"""Real-data regression tests for identity, outcome provenance and training exclusion."""

from decimal import Decimal
from hashlib import sha256
from io import StringIO
from pathlib import Path
import csv
import json
import socket
import shutil
import subprocess
import sys
import uuid
import zipfile

import pandas as pd
import pytest
import yaml
import requests

from agri_data.contracts.canonical import reconcile_reference
from agri_data.contracts.ml_dataset import export_preparation, load_training_snapshot
from agri_data.contracts.postgres import PostgresStore
from agri_data.contracts.trials import import_woburn, workbook_rows
from agri_data.contracts.assets import archive_response
from agri_data.contracts.health import check_snapshot


ROOT = Path(__file__).resolve().parents[2]


def context():
    config = yaml.safe_load((ROOT / "config" / "acceptance.yaml").read_bytes())
    db = config["database"]
    store = PostgresStore(db["expected_database"], db["expected_user"], db["acceptance_schema"])
    manifest = ROOT / config["trial_corpus_manifest"]
    if not manifest.is_file():
        raise RuntimeError("Acquire the genuine Woburn corpus and configure its reference before running tests")
    return store, ROOT / config["reference_corpus_manifest"], manifest


def test_reconciliation_deduplicates_real_receipts_without_losing_values():
    store, corpus_path, _ = context()
    first = reconcile_reference(store, corpus_path)
    second = reconcile_reference(store, corpus_path)
    assert first == second
    with store.session() as connection:
        mappings = connection.execute(
            "SELECT o.record,c.scientific_record FROM observation_evidence e "
            "JOIN observations o USING(observation_id) "
            "JOIN canonical_observations c USING(canonical_observation_id)"
        ).fetchall()
        collapsed = connection.execute(
            "SELECT count(*) FROM (SELECT canonical_observation_id FROM observation_evidence "
            "GROUP BY canonical_observation_id HAVING count(*)>1) repeated"
        ).fetchone()[0]
        assert collapsed > 0
        assert connection.execute("SELECT count(*) FROM canonical_fields").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM accepted_canonical_observations").fetchone()[0] == 0
    for raw, canonical in mappings:
        assert raw["value_numeric"] == canonical["value_numeric"]
        assert raw["original_value"] == canonical["original_value"]
        assert raw["observed_at"] == canonical["observed_at"]
        assert raw["source_record_locator"] == canonical["source_record_locator"]
        if raw["variable_id"] == "daily_rainfall":
            assert canonical["standardized_unit"] == "mm"
            assert canonical["original_unit"] == "mm/day"


def test_real_trial_yields_match_csv_and_independent_workbook():
    store, _, manifest_path = context()
    first = import_woburn(store, manifest_path)
    repeated = import_woburn(store, manifest_path)
    assert repeated["inserted"] == 0
    manifest = json.loads(manifest_path.read_bytes())
    asset = manifest["data"]
    assert sha256(Path(asset["raw_path"]).read_bytes()).hexdigest() == asset["raw_sha256"]
    with zipfile.ZipFile(asset["raw_path"]) as archive:
        csv_rows = list(csv.DictReader(StringIO(
            archive.read("01-WRN3-WH7618/crop_data.csv").decode("utf-8"))))
        spreadsheet = workbook_rows(archive.read("01-WRN3-WH7618.xlsx"), 3)
    with store.session() as connection:
        records = connection.execute(
            "SELECT source_record_locator,yield_kg_ha,raw_record,record_context,validation_status "
            "FROM crop_performance WHERE source_asset_id=%s", (asset["raw_sha256"],)
        ).fetchall()
    assert len(records) == len(csv_rows) == first["persisted"]
    missing = 0
    ambiguous = 0
    for locator, value, raw, metadata, status in records:
        row_number = int(locator.rsplit(":", 1)[1])
        assert raw == csv_rows[row_number - 2]
        workbook_value = spreadsheet[row_number - 1]["U" + str(row_number)]
        assert status == "pending"
        assert metadata["decision_at"] is None
        if raw["grain_yield"] == "*":
            assert value is None and workbook_value == "*"
            missing += 1
        else:
            assert value == float(Decimal(raw["grain_yield"]) * 1000)
            # The published CSV rounds the original workbook numbers. Compare
            # exact decimal representations at the CSV's recorded precision.
            published = Decimal(raw["grain_yield"])
            precision = Decimal(1).scaleb(published.as_tuple().exponent)
            assert Decimal(workbook_value).quantize(precision) == published
        ambiguous += metadata["source_plot_code_not_unique"]
    assert missing > 0
    assert ambiguous > 0  # Genuine source plot-code collisions are retained, not merged.


def test_preparation_snapshot_is_reproducible_and_refuses_training():
    store, _, _ = context()
    base = ROOT / "data" / "exports" / ("ml-regression-" + uuid.uuid4().hex)
    config = ROOT / "config" / "ml_dataset.yaml"
    reports = [export_preparation(store, config, base / name, ROOT) for name in ("first", "second")]
    assert reports[0] == reports[1]
    manifests = [json.loads((base / name / "manifest.json").read_bytes()) for name in ("first", "second")]
    assert manifests[0]["snapshot_id"] == manifests[1]["snapshot_id"]
    for name, manifest in zip(("first", "second"), manifests):
        assert manifest["training_ready"] is False
        for item in manifest["files"]:
            assert sha256((base / name / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    with pytest.raises(ValueError, match="not an approved training"):
        load_training_snapshot(base / "first")
    examples = pd.read_parquet(base / "first" / "examples.parquet")
    targets = pd.read_parquet(base / "first" / "targets.parquet")
    splits = pd.read_parquet(base / "first" / "splits.parquet")
    assert not examples["context_id"].duplicated().any()
    assert examples["decision_at"].isna().all()
    assert targets["value"].isna().any()
    assert set(splits["split"]) == {"withheld"}
    assert set(examples["example_id"]) == set(targets["example_id"]) == set(splits["example_id"])


def test_real_http_refusal_records_failure_without_a_raw_observation():
    output = ROOT / "data" / "exports" / ("http-refusal-" + uuid.uuid4().hex)
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        with pytest.raises(requests.RequestException):
            archive_response(f"http://127.0.0.1:{endpoint.getsockname()[1]}/", output, timeout=1)
    files = list(output.iterdir())
    assert len(files) == 1 and files[0].name.endswith(".failure.json")
    result = json.loads(files[0].read_bytes())
    assert result["status"] == "failed"
    assert "raw_path" not in result


def test_live_engineering_health_accepts_pending_data_and_preserves_missingness(tmp_path):
    output = ROOT / "data" / "exports" / ("engineering-health-" + uuid.uuid4().hex)
    process = subprocess.run(
        [sys.executable, "-m", "agri_data", "health-check", "--config",
         str(ROOT / "config" / "acceptance.yaml"), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads(process.stdout)
    assert report["status"] == "passed", report
    assert report["verified_fresh_requests"] == 6
    assert all(receipt["fresh"] and receipt["http_status"] == 200 for receipt in report["request_evidence"])
    formats = report["data"]["format_checks"]
    assert formats["training_ready"] is False
    assert formats["missing_yields"] > 0
    assert report["full_inventory_complete"] is False
    corrupt = tmp_path / "corrupt-snapshot"
    shutil.copytree(output / "dataset", corrupt)
    with (corrupt / "targets.parquet").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        check_snapshot(corrupt)


def test_engineering_cli_reports_missing_configuration_without_a_traceback(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "agri_data", "health-check", "--config",
         str(tmp_path / "absent.yaml"), "--output", str(tmp_path / "output")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "FileNotFoundError" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "output").exists()
