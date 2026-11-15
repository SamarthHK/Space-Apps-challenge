"""Tests using actual archived provider bytes and the real acceptance database.

Missing corpus/database is a test failure, never a skip, mock or generated fixture.
These limited checks do not certify full Plan.md acceptance.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import os
import socket
import subprocess
import sys

import geopandas as gpd
import psycopg
import pytest
import yaml
from shapely.geometry import shape

from agri_data.contracts.postgres import PostgresStore


ROOT = Path(__file__).resolve().parents[2]


def context():
    config = yaml.safe_load((ROOT / "config" / "acceptance.yaml").read_text(encoding="utf-8"))
    corpus = json.loads((ROOT / config["reference_corpus_manifest"]).read_bytes())
    db = config["database"]
    return corpus, PostgresStore(db["expected_database"], db["expected_user"], db["acceptance_schema"])


def test_raw_provider_values_match_independent_sql_readback():
    corpus, store = context()
    asset = corpus["weather_asset"]
    payload = Path(asset["raw_path"]).read_bytes()
    assert sha256(payload).hexdigest() == asset["raw_sha256"]
    raw = json.loads(payload)
    with store.session() as connection:
        rows = connection.execute(
            "SELECT value_numeric, standardized_unit, observed_at, record FROM observations "
            "WHERE extraction_job_id=%s", (asset["request_id"],)
        ).fetchall()
    expected_count = sum(
        value is not None and value != raw["header"]["fill_value"]
        for dates in raw["properties"]["parameter"].values() for value in dates.values()
    )
    assert len(rows) == expected_count > 0
    for value, unit, observed_at, record in rows:
        _, _, _, code, day = record["source_record_locator"].split("/")
        assert value == raw["properties"]["parameter"][code][day]
        assert record["original_value"] == raw["properties"]["parameter"][code][day]
        assert unit == raw["parameters"][code]["units"]
        assert observed_at == datetime.strptime(day, "%Y%m%d")
        assert record["timezone"] == raw["header"]["time_standard"]
        assert record["validation_status"] == "pending"
        assert record["raw_sha256"] == asset["raw_sha256"]


def test_actual_kml_matches_provider_rings_and_postgis():
    corpus, store = context()
    parcel = json.loads(Path(corpus["parcel_asset"]["raw_path"]).read_bytes())
    source = shape(parcel["geometry"])
    translated = gpd.read_file(corpus["kml_path"]).geometry.iloc[0]
    assert translated.equals_exact(source, 1e-12)
    with store.session() as connection:
        row = connection.execute(
            "SELECT ST_AsGeoJSON(geometry,15),ST_IsValid(geometry),ST_SRID(geometry) "
            "FROM field_boundaries WHERE field_id=%s", ("PDOK_" + parcel["id"],)
        ).fetchone()
    assert row[1] and row[2] == 4326
    assert shape(json.loads(row[0])).equals_exact(source, 1e-12)


def test_actual_refused_connection_does_not_create_a_fallback_database():
    # A bound, non-listening port produces an actual local connection refusal.
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
        failed = False
        try:
            psycopg.connect(host="127.0.0.1", port=port, dbname="agri_acceptance",
                            user="agri_acceptance", connect_timeout=2)
        except psycopg.OperationalError:
            failed = True
        assert failed
        environment = dict(os.environ)
        environment["DATABASE_URL"] = f"postgresql://agri_acceptance@127.0.0.1:{port}/agri_acceptance"
        process = subprocess.run(
            [sys.executable, "-m", "agri_data.contracts.storage_proof", "--read-job",
             context()[0]["weather_asset"]["request_id"], "--database", "agri_acceptance",
             "--user", "agri_acceptance", "--schema", "agri_contracts"],
            capture_output=True, text=True, env=environment,
        )
        assert process.returncode != 0
        assert "row_count" not in process.stdout


def test_existing_variable_cannot_be_attached_to_another_existing_feature():
    _, store = context()
    with store.session() as connection:
        observation_id, original_feature = connection.execute(
            "SELECT observation_id,feature_id FROM observations ORDER BY observation_id LIMIT 1"
        ).fetchone()
        different_feature = connection.execute(
            "SELECT feature_id FROM variables WHERE feature_id<>%s LIMIT 1", (original_feature,)
        ).fetchone()[0]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with connection.transaction():
                connection.execute(
                    "UPDATE observations SET feature_id=%s WHERE observation_id=%s",
                    (different_feature, observation_id),
                )
        assert connection.execute(
            "SELECT feature_id FROM observations WHERE observation_id=%s", (observation_id,)
        ).fetchone()[0] == original_feature
