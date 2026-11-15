"""Read-only reconciliation with real PostgreSQL and archived provider evidence."""

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
import psycopg
import pytest
from jsonschema import Draft202012Validator, FormatChecker

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from agri_data.api.data import DataSettings, DataStore, DataUnavailable
from agri_data.api.pagination import Pagination, InvalidCursor, ChangedSnapshot


@pytest.fixture(scope="module")
def data_settings():
    settings = DataSettings.from_env({
        key.replace("AGRI_TEST_", "AGRI_API_"): value for key, value in os.environ.items()
        if key.startswith("AGRI_TEST_")
    })
    assert settings is not None, "Configure AGRI_TEST_DATABASE_* / SCHEMA / PROJECT_IDS against authentic data"
    assert DataStore(settings).available(), "Real PostgreSQL canonical corpus must be prepared"
    return settings


@pytest.fixture(scope="module")
def client(data_settings):
    settings = Settings.from_env({"AGRI_ALLOWED_ORIGINS": "http://localhost:1080"})
    with TestClient(create_app(settings, data_settings), base_url="http://localhost") as client:
        yield client


@pytest.fixture(scope="module")
def authentic(data_settings):
    with DataStore(data_settings).session() as connection:
        row = connection.execute(
            "SELECT c.field_id,c.canonical_observation_id,c.scientific_record,a.path,a.raw_sha256,o.record "
            "FROM canonical_observations c JOIN canonical_fields f USING(field_id) "
            "JOIN observation_evidence e USING(canonical_observation_id) "
            "JOIN observations o USING(observation_id) JOIN source_assets a ON a.source_asset_id=e.source_asset_id "
            "WHERE f.project_id=ANY(%s) AND o.source_id='SRC-004' ORDER BY c.canonical_observation_id LIMIT 1",
            (list(data_settings.project_ids),),
        ).fetchone()
    assert row is not None, "Authentic canonical NASA record is required"
    payload = Path(row[3]).read_bytes()
    assert sha256(payload).hexdigest() == row[4]
    return row, json.loads(payload)


def test_configuration_requires_complete_explicit_scope():
    assert DataSettings.from_env({}) is None
    with pytest.raises(ValueError):
        DataSettings.from_env({"AGRI_API_SCHEMA": "agri_contracts"})


def test_real_fields_exclude_aliases_and_require_boundary_selection(client, data_settings):
    response = client.get("/api/v1/fields")
    assert response.status_code == 200, response.text
    fields = response.json()["data"]
    with DataStore(data_settings).session() as connection:
        expected = connection.execute(
            "SELECT field_id FROM canonical_fields WHERE project_id=ANY(%s) ORDER BY field_id",
            (list(data_settings.project_ids),),
        ).fetchall()
    assert [item["field_id"] for item in fields] == [row[0] for row in expected]
    assert fields, "Authentic fields must exist"
    for item in fields:
        if len(item["boundary_versions"]) > 1:
            assert item["geometry"] is None
            assert item["current_boundary_id"] is None
            assert item["geometry_status"] == "selection_required"
        for version in item["boundary_versions"]:
            selected = client.get(f"/api/v1/fields/{item['field_id']}",
                                  params={"boundary_id": version["boundary_id"]})
            assert selected.status_code == 200
            actual = selected.json()["data"]
            with DataStore(data_settings).session() as connection:
                geometry = connection.execute(
                    "SELECT ST_AsGeoJSON(geometry,15) FROM field_boundaries WHERE boundary_id=%s",
                    (version["boundary_id"],),
                ).fetchone()[0]
            assert actual["geometry"] == json.loads(geometry)
            assert actual["selected_boundary_id"] == version["boundary_id"]
            if actual["area_m2"] is not None:
                assert actual["area_ha"] == actual["area_m2"] / 10000
        assert client.get(f"/api/v1/fields/{item['field_id']}",
                          params={"boundary_id": "not-a-boundary"}).status_code == 404


def test_observation_and_evidence_preserve_provider_meaning(client, authentic):
    row, raw = authentic
    field_id, identifier, scientific, _, _, evidence = row
    response = client.get(f"/api/v1/fields/{field_id}/observations/{identifier}")
    assert response.status_code == 200, response.text
    actual = response.json()["data"]
    assert actual["scientific_record"] == scientific
    assert actual["validation_status"] == "pending"
    records = client.get(f"/api/v1/fields/{field_id}/observations/{identifier}/evidence").json()["data"]
    matching = next(record for record in records if record["observation_id"] == evidence["observation_id"])
    _, _, _, parameter, day = matching["source_record_locator"].split("/")
    assert matching["value_numeric"] == raw["properties"]["parameter"][parameter][day]
    assert matching["original_unit"] == raw["parameters"][parameter]["units"]
    assert matching["timezone"] == raw["header"]["time_standard"]
    assert "raw_path" not in json.dumps(actual) and "DATABASE_URL" not in json.dumps(records)
    schema = client.get("/api/v1/openapi.json").json()
    Draft202012Validator({
        "components": schema["components"],
        "$ref": "#/components/schemas/EvidenceResponse",
    }, format_checker=FormatChecker()).validate({
        "data": records, "meta": {"api_version": "v1", "request_id": "schema-check", "next_cursor": None},
    })


def test_real_pagination_filters_and_tampering(client, authentic, data_settings):
    field_id = authentic[0][0]
    endpoint = f"/api/v1/fields/{field_id}/observations"
    first = client.get(endpoint, params={"limit": 2}).json()
    assert len(first["data"]) == 2
    cursor = first["meta"]["next_cursor"]
    assert cursor
    second = client.get(endpoint, params={"limit": 2, "cursor": cursor}).json()
    assert not {row["canonical_observation_id"] for row in first["data"]}.intersection(
        row["canonical_observation_id"] for row in second["data"])
    assert client.get(endpoint, params={"cursor": cursor + "x"}).status_code == 400
    assert client.get(endpoint, params={"cursor": cursor, "validation_status": "pending"}).status_code == 400
    accepted = client.get(endpoint, params={"validation_status": "accepted"})
    assert accepted.status_code == 200 and accepted.json()["data"] == []
    assert client.get(endpoint, params={"validation_status": "verified"}).status_code == 422
    assert client.get(endpoint, params={"start_date": "2025-01-01"}).status_code == 422
    assert client.get(endpoint, params={"start_date": "2025-02-01", "end_date": "2025-01-01"}).status_code == 422
    observed = authentic[0][2]["observed_at"][:10]
    daily = client.get(endpoint, params={"start_date": observed, "end_date": observed}).json()["data"]
    assert daily and all(item["scientific_record"]["observed_at"][:10] == observed for item in daily)
    rows = DataStore(data_settings).observations(field_id)
    assert len(rows) == len({item["canonical_observation_id"] for item in rows})
    assert any(item["evidence_count"] > 1 for item in rows), "Repeated authentic receipts required"


def test_existing_resources_are_inaccessible_outside_project_scope(data_settings, authentic):
    settings = Settings.from_env({"AGRI_ALLOWED_ORIGINS": "http://localhost:1080"})
    field_id, identifier = authentic[0][:2]
    with TestClient(create_app(settings, replace(data_settings, project_ids=())), base_url="http://localhost") as client:
        assert client.get("/api/v1/fields").json()["data"] == []
        for suffix in ("", "/observations", f"/observations/{identifier}",
                       f"/observations/{identifier}/evidence"):
            assert client.get(f"/api/v1/fields/{field_id}" + suffix).status_code == 404


def test_snapshot_changes_and_restarts_invalidate_cursors(data_settings, authentic):
    rows = DataStore(data_settings).observations(authentic[0][0])
    pagination = Pagination()
    _, cursor = pagination.page(rows, ["authentic"], 1)
    with pytest.raises(ChangedSnapshot):
        pagination.page(rows[1:], ["authentic"], 1, cursor)
    with pytest.raises(InvalidCursor):
        Pagination().page(rows, ["authentic"], 1, cursor)


def test_schema_and_identity_mismatches_fail_closed(data_settings):
    for invalid in (replace(data_settings, schema="agri_missing_api_schema"),
                    replace(data_settings, database="not_the_configured_database")):
        assert not DataStore(invalid).available()
        with pytest.raises(DataUnavailable):
            DataStore(invalid).fields()


def test_api_transactions_reject_writes(data_settings):
    with DataStore(data_settings).session() as connection:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            connection.execute("CREATE TABLE api_must_not_create (id integer)")
