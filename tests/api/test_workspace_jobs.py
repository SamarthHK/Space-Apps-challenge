from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
import os
import subprocess
import sys
import zipfile

from fastapi.testclient import TestClient
from psycopg import sql
import pytest
from shapely import force_2d
from shapely.geometry import shape

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from agri_data.api.data import DataStore
from agri_data.api.field_writes import FieldCreate, FieldPatch
from agri_data.workspace.errors import WorkspaceError
from agri_data.workspace.fields import FieldStore, field_etag
from agri_data.workspace.formats import parse_upload, serialize_export
from agri_data.workspace.jobs import JobStore


ORIGIN = "http://127.0.0.1:1080"


def upload(geometry, count=1, name="Original provider geometry copy"):
    return json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "provider-copy-" + str(index), "geometry": geometry,
         "properties": {"name": name, "source_note": "Unchanged real provider geometry; integration test copy"}}
        for index in range(count)
    ]}).encode()


def preview(jobs, geometry, key="upload", count=1, name="Original provider geometry copy"):
    submitted = jobs.submit_import(upload(geometry, count, name), "provider.geojson",
                                   "boundary-integration", "provider-copies", key)
    assert jobs.run_once("preview-worker")
    assert jobs.get(submitted["job_id"])["status"] == "succeeded"
    return jobs.import_info(submitted["resource_id"])


def confirmation(info):
    return {"preview_hash": info["preview_hash"],
            "candidate_ids": [row["candidate_id"] for row in info["candidates"]]}


def test_preview_changes_no_canonical_rows_and_confirmation_is_idempotent(field_store, actual_geometry):
    jobs = JobStore(field_store)
    info = preview(jobs, actual_geometry)
    assert len(info["candidates"]) == 1 and not info["rejected"]
    with field_store.workspace.session() as connection:
        for name in ("fields", "source_assets", "field_boundaries", "canonical_observations"):
            assert connection.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(
                field_store.table(name))).fetchone()["n"] == 0
    submitted = jobs.confirm(info["import_id"], confirmation(info), "confirm")
    assert jobs.confirm(info["import_id"], confirmation(info), "confirm") == submitted
    assert jobs.run_once("confirm-worker")
    result = jobs.get(submitted["job_id"])
    assert result["status"] == "succeeded" and len(result["result"]["fields"]) == 1
    assert jobs.confirm(info["import_id"], confirmation(info), "another-confirm")["job_id"] == submitted["job_id"]
    stored = DataStore(field_store.settings).fields()[0]
    assert shape(stored["geometry"]).equals_exact(force_2d(shape(actual_geometry)), 1e-12)
    assert len(stored["boundary_versions"]) == 1


def test_confirm_batch_rolls_back_and_retries_after_real_database_failure(field_store, actual_geometry):
    jobs = JobStore(field_store)
    info = preview(jobs, actual_geometry, count=2)
    blocked = sorted(row["field_id"] for row in info["candidates"])[-1]
    with field_store.workspace.session() as connection:
        connection.execute(sql.SQL(
            "ALTER TABLE workspace_field_revisions ADD CONSTRAINT batch_rollback_probe CHECK(field_id <> {})"
        ).format(sql.Literal(blocked)))
    job = jobs.confirm(info["import_id"], confirmation(info), "confirm-batch")
    jobs.run_once("first-worker")
    assert jobs.get(job["job_id"])["status"] == "queued"
    assert DataStore(field_store.settings).fields() == []
    with field_store.workspace.session() as connection:
        assert connection.execute("SELECT count(*) AS n FROM workspace_field_revisions").fetchone()["n"] == 0
        connection.execute("ALTER TABLE workspace_field_revisions DROP CONSTRAINT batch_rollback_probe")
        connection.execute("UPDATE workspace_jobs SET available_at=clock_timestamp() WHERE job_id=%s", (job["job_id"],))
    jobs.run_once("retry-worker")
    result = jobs.get(job["job_id"])
    assert result["status"] == "succeeded" and result["attempts"] == 2
    assert len(DataStore(field_store.settings).fields()) == 2


def test_stale_preview_cannot_overwrite_a_later_field_edit(field_store, actual_geometry):
    jobs = JobStore(field_store)
    original = preview(jobs, actual_geometry)
    created = jobs.confirm(original["import_id"], confirmation(original), "original-confirm")
    jobs.run_once("worker")
    field_id = jobs.get(created["job_id"])["result"]["fields"][0]["field_id"]
    newer = preview(jobs, actual_geometry, key="newer-upload", name="Imported name change")
    assert newer["candidates"][0]["expected_version"] == 1
    field_store.update(field_id, FieldPatch(name="More recent manual edit"), field_etag(field_id, 1), "manual")
    stale = jobs.confirm(newer["import_id"], confirmation(newer), "stale-confirm")
    jobs.run_once("worker")
    result = jobs.get(stale["job_id"])
    assert result["status"] == "failed" and result["error"]["code"] == "version_conflict"
    assert DataStore(field_store.settings).get_field(field_id)["name"] == "More recent manual edit"


def test_two_workers_cannot_claim_the_same_job(field_store, actual_geometry):
    jobs = JobStore(field_store)
    submitted = jobs.submit_import(upload(actual_geometry), "field.geojson", "boundary-integration", "source", "upload")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(jobs.claim, ["worker-one", "worker-two"]))
    assert sum(claim is not None for claim in claims) == 1
    assert jobs.get(submitted["job_id"])["attempts"] == 1
    with field_store.workspace.session() as connection:
        connection.execute(
            "UPDATE workspace_jobs SET attempts=3,lease_until=clock_timestamp()-interval '1 second' WHERE job_id=%s",
            (submitted["job_id"],),
        )
    assert jobs.claim("last-worker") is None
    assert jobs.get(submitted["job_id"])["error"]["code"] == "attempt_limit"


def test_job_survives_process_exit_and_a_different_worker_recovers_its_lease(field_store, actual_geometry):
    jobs = JobStore(field_store)
    submitted = jobs.submit_import(upload(actual_geometry), "field.geojson", "boundary-integration", "source", "durable")
    settings, source = field_store.workspace.settings, field_store.settings
    environment = dict(os.environ, AGRI_WORKSPACE_DATABASE_URL=settings.dsn,
        AGRI_WORKSPACE_DATABASE_NAME=settings.database, AGRI_WORKSPACE_DATABASE_USER=settings.user,
        AGRI_WORKSPACE_SCHEMA=settings.schema, AGRI_WORKSPACE_ID=settings.workspace_id,
        AGRI_API_DATABASE_URL=source.dsn, AGRI_API_DATABASE_NAME=source.database, AGRI_API_DATABASE_USER=source.user,
        AGRI_API_SCHEMA=source.schema, AGRI_API_PROJECT_IDS=",".join(source.project_ids))
    crash = subprocess.run([sys.executable, "-c",
        "from agri_data.workspace.settings import WorkspaceSettings;"
        "from agri_data.workspace.store import WorkspaceStore;"
        "from agri_data.workspace.fields import FieldStore;"
        "from agri_data.workspace.jobs import JobStore;"
        "from agri_data.api.data import DataSettings;"
        "JobStore(FieldStore(WorkspaceStore(WorkspaceSettings.from_env()),DataSettings.from_env())).claim('exited-process')"],
        env=environment, capture_output=True, text=True)
    assert crash.returncode == 0, crash.stderr
    assert jobs.get(submitted["job_id"])["status"] == "running"
    with field_store.workspace.session() as connection:
        connection.execute("UPDATE workspace_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE job_id=%s",
                           (submitted["job_id"],))
    recovered = subprocess.run([sys.executable, "-m", "agri_data.workspace.worker", "--once"],
                               env=environment, capture_output=True, text=True)
    assert recovered.returncode == 0, recovered.stderr
    assert jobs.get(submitted["job_id"])["status"] == "succeeded"
    assert jobs.get(submitted["job_id"])["attempts"] == 2
    assert not jobs.available()


@pytest.mark.parametrize("format_name", ["geojson", "kml", "kmz"])
def test_exports_roundtrip_actual_geometry_and_require_scoped_downloads(field_store, actual_geometry, format_name):
    jobs = JobStore(field_store)
    created = field_store.create(FieldCreate(project_id="boundary-integration", name="Actual geometry export",
        geometry=actual_geometry), "create", "export-source")
    job = jobs.submit_export({"format": format_name, "fields": [{
        "field_id": created["field_id"], "boundary_id": created["current_boundary_id"]}]}, "export")
    with pytest.raises(WorkspaceError) as pending:
        jobs.download(job["resource_id"])
    assert pending.value.status == 409
    jobs.run_once("export-worker")
    assert jobs.get(job["job_id"])["status"] == "succeeded"
    exported = jobs.download(job["resource_id"])
    content = bytes(exported["content"])
    assert sha256(content).hexdigest() == exported["sha256"]
    candidates, rejected = parse_upload(content, exported["filename"], "boundary-integration", "roundtrip")
    assert not rejected and len(candidates) == 1
    assert shape(candidates[0]["original_geometry"]).equals_exact(shape(actual_geometry), 1e-12)
    restricted = JobStore(FieldStore(field_store.workspace, replace(field_store.settings, project_ids=("other",))))
    for lookup, identifier in [(restricted.get, job["job_id"]), (restricted.download, job["resource_id"])]:
        with pytest.raises(WorkspaceError) as denied:
            lookup(identifier)
        assert denied.value.status == 404
    assert restricted.claim("unscoped-worker") is None
    field_store.update(created["field_id"], None, field_etag(created["field_id"], 1), "archive", archive=True)
    with pytest.raises(WorkspaceError) as archived:
        jobs.download(job["resource_id"])
    assert archived.value.status == 404


def test_invalid_archives_fail_without_creating_fields(field_store, actual_geometry):
    jobs = JobStore(field_store)
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../outside.kml", b"<kml/>")
    job = jobs.submit_import(output.getvalue(), "unsafe.kmz", "boundary-integration", "unsafe", "unsafe")
    jobs.run_once("worker")
    assert jobs.get(job["job_id"])["error"]["code"] == "invalid_import"
    assert DataStore(field_store.settings).fields() == []


@pytest.mark.parametrize("format_name", ["geojson", "kml", "kmz"])
def test_topology_only_probe_retains_parts_holes_altitude_and_metadata(field_store, format_name):
    # Diagnostic topology in an owned disposable schema, never authentic field/provider evidence.
    geometry = {"type": "MultiPolygon", "coordinates": [
        [[[10, 10, 3], [14, 10, 4], [14, 14, 5], [10, 14, 6], [10, 10, 3]],
         [[11, 11, 3], [11, 12, 3], [12, 12, 3], [12, 11, 3], [11, 11, 3]]],
        [[[15, 10, 3], [16, 10, 3], [16, 11, 3], [15, 11, 3], [15, 10, 3]]],
    ]}
    features = [{"type": "Feature", "id": "topology-probe", "geometry": geometry, "properties": {
        "name": "Topology probe, not a real field", "source_metadata": {"folders": ["Folder & <text>"],
        "description": "<untrusted text>", "provider_identifier": "unchanged"},
    }}]
    content = serialize_export(features, format_name)
    candidates, rejected = parse_upload(content, "probe." + format_name, "topology-only", "diagnostic")
    assert not rejected and len(candidates) == 1
    assert json.loads(json.dumps(candidates[0]["original_geometry"])) == geometry
    if format_name == "geojson":
        assert candidates[0]["metadata"] == features[0]["properties"]
    else:
        assert candidates[0]["metadata"]["folders"] == ["Folder & <text>"]
        values = {item["name"]: json.loads(item["value"]) for item in candidates[0]["metadata"]["extended_data"]}
        assert values["source_metadata"] == features[0]["properties"]["source_metadata"]
    jobs = JobStore(field_store)
    submitted = jobs.submit_import(content, "probe." + format_name, "boundary-integration", "diagnostic", "topology")
    jobs.run_once("topology-preview")
    assert jobs.get(submitted["job_id"])["status"] == "succeeded"
    info = jobs.import_info(submitted["resource_id"])
    confirmed = jobs.confirm(info["import_id"], confirmation(info), "topology-confirm")
    jobs.run_once("topology-confirm")
    assert jobs.get(confirmed["job_id"])["status"] == "succeeded"
    stored = DataStore(field_store.settings).fields()[0]
    assert shape(stored["geometry"]).equals_exact(force_2d(shape(geometry)), 1e-12)
    assert DataStore(field_store.settings).observations(stored["field_id"]) == []
    exported = jobs.submit_export({"format": format_name, "fields": [{
        "field_id": stored["field_id"], "boundary_id": stored["selected_boundary_id"]}]}, "topology-export")
    jobs.run_once("topology-export")
    assert jobs.get(exported["job_id"])["status"] == "succeeded"
    download = jobs.download(exported["resource_id"])
    persisted, rejected = parse_upload(bytes(download["content"]), download["filename"], "topology-only", "diagnostic")
    assert not rejected
    assert json.loads(json.dumps(persisted[0]["original_geometry"])) == geometry


def test_job_http_contract_exposes_binary_download_and_honest_worker_readiness(field_store, actual_geometry):
    jobs = JobStore(field_store)
    app = create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}),
                     field_store.settings, field_store.workspace.settings)
    with TestClient(app, base_url="http://127.0.0.1", headers={"Origin": ORIGIN}) as http:
        def capabilities():
            return {item["capability_id"]: item for item in http.get("/api/v1/workspace").json()["data"]["capabilities"]}
        assert capabilities()["imports"]["state"] == "blocked"
        jobs.heartbeat("live-test-worker")
        assert capabilities()["imports"]["state"] == "ready"
        assert capabilities()["acquisition"]["state"] == "not_implemented"
        response = http.post("/api/v1/imports", params={"filename": "real.geojson",
            "project_id": "boundary-integration", "source_namespace": "real"},
            content=upload(actual_geometry), headers={"Content-Type": "application/octet-stream",
                                                       "Idempotency-Key": "http-import"})
        assert response.status_code == 202, response.text
        assert response.headers["Location"].startswith("/api/v1/jobs/")
        jobs.run_once("worker")
        info_response = http.get("/api/v1/imports/" + response.json()["data"]["resource_id"])
        assert info_response.status_code == 200, info_response.text
        info = info_response.json()["data"]
        confirmed = http.post("/api/v1/imports/" + info["import_id"] + "/confirm",
            json=confirmation(info), headers={"Idempotency-Key": "http-confirm"})
        assert confirmed.status_code == 202
        jobs.run_once("worker")
        selected = jobs.get(confirmed.json()["data"]["job_id"])["result"]["fields"][0]
        exported = http.post("/api/v1/exports", json={"format": "kmz", "fields": [{
            "field_id": selected["field_id"], "boundary_id": selected["current_boundary_id"]}]},
            headers={"Idempotency-Key": "http-export"})
        assert exported.status_code == 202
        jobs.run_once("worker")
        download = http.get("/api/v1/exports/" + exported.json()["data"]["resource_id"] + "/download")
        assert download.status_code == 200
        assert download.headers["Content-Type"] == "application/vnd.google-earth.kmz"
        assert "attachment;" in download.headers["Content-Disposition"]
        assert "Content-Disposition" in download.headers["Access-Control-Expose-Headers"]
        assert zipfile.is_zipfile(BytesIO(download.content))
