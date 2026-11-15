from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace

from fastapi.testclient import TestClient
from psycopg import sql
import pytest
from shapely.geometry import shape

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from agri_data.api.data import DataStore
from agri_data.api.field_writes import FieldCreate, FieldPatch
from agri_data.workspace.errors import WorkspaceError, WorkspaceUnavailable
from agri_data.workspace.fields import FieldStore, field_etag


ORIGIN = "http://127.0.0.1:1080"


def create(field_store, actual_geometry, key="field-creation"):
    return field_store.create(FieldCreate(project_id="boundary-integration", name="Actual provider boundary copy",
                                         geometry=actual_geometry), key, "field-test")


def test_create_edit_archive_preserves_history_and_original_bytes(field_store, actual_geometry):
    result = create(field_store, actual_geometry)
    reader = DataStore(field_store.settings)
    first = reader.get_field(result["field_id"])
    assert shape(first["geometry"]).equals_exact(shape(actual_geometry), 1e-12)
    assert first["area_m2"] > 0 and first["current_boundary_id"] == result["current_boundary_id"]
    updated = field_store.update(result["field_id"], FieldPatch(name=None, geometry=actual_geometry),
                                 field_etag(result["field_id"], 1), "edit-test")
    assert updated["version"] == 2
    current = reader.get_field(result["field_id"])
    assert current["name"] is None and len(current["boundary_versions"]) == 2
    old = reader.get_field(result["field_id"], first["selected_boundary_id"])
    assert old["selected_boundary_id"] == first["selected_boundary_id"]
    assert old["current_boundary_id"] == updated["current_boundary_id"]
    assert old["area_m2"] == pytest.approx(current["area_m2"], rel=1e-10)
    archived = field_store.update(result["field_id"], None, field_etag(result["field_id"], 2), "archive", archive=True)
    assert archived["archived"] and reader.fields() == []
    with field_store.workspace.session() as connection:
        assert connection.execute("SELECT count(*) AS n FROM workspace_field_revisions").fetchone()["n"] == 3
        assert connection.execute("SELECT count(*) AS n FROM workspace_assets").fetchone()["n"] == 2
        assert connection.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(
            field_store.table("canonical_observations"))).fetchone()["n"] == 0


def test_idempotent_create_is_atomic_and_different_input_conflicts(field_store, actual_geometry):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(field_store, actual_geometry), range(2)))
    assert results[0] == results[1]
    assert len(DataStore(field_store.settings).fields()) == 1
    with pytest.raises(WorkspaceError) as failure:
        field_store.create(FieldCreate(project_id="boundary-integration", name="Different request",
            geometry=actual_geometry), "field-creation", "conflict")
    assert failure.value.status == 409


def test_field_writes_require_versions_and_explicit_project_scope(field_store, actual_geometry):
    created = create(field_store, actual_geometry)
    identifier = created["field_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        def update(name):
            try:
                field_store.update(identifier, FieldPatch(name=name), field_etag(identifier, 1), "race")
                return 200
            except WorkspaceError as error:
                return error.status
        assert sorted(pool.map(update, ["First rename", "Second rename"])) == [200, 412]
    restricted = FieldStore(field_store.workspace, replace(field_store.settings, project_ids=("other",)))
    with pytest.raises(WorkspaceError) as denied:
        restricted.update(identifier, FieldPatch(name="denied"), field_etag(identifier, 2), "scope")
    assert denied.value.status == 404
    with pytest.raises(WorkspaceError) as missing:
        field_store.update(identifier, FieldPatch(name="no precondition"), None, "missing")
    assert missing.value.status == 428


def test_field_transaction_rolls_back_assets_and_idempotency_on_audit_failure(field_store, actual_geometry):
    with field_store.workspace.session() as connection:
        connection.execute("ALTER TABLE workspace_field_revisions ADD CONSTRAINT rollback_probe CHECK (version < 1)")
    with pytest.raises(WorkspaceUnavailable):
        create(field_store, actual_geometry)
    assert DataStore(field_store.settings).fields() == []
    with field_store.workspace.session() as connection:
        for table in ("workspace_assets", "workspace_idempotency", "workspace_field_revisions"):
            assert connection.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(
                sql.Identifier(table))).fetchone()["n"] == 0


def test_field_http_contract_and_geometry_rejections(field_store, actual_geometry):
    app = create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}),
                     field_store.settings, field_store.workspace.settings)
    with TestClient(app, base_url="http://127.0.0.1", headers={"Origin": ORIGIN}) as http:
        capabilities = http.get("/api/v1/workspace").json()["data"]["capabilities"]
        assert next(row for row in capabilities if row["capability_id"] == "field_writes")["state"] == "ready"
        body = {"project_id": "boundary-integration", "name": "HTTP boundary copy", "geometry": actual_geometry}
        assert http.post("/api/v1/fields", json=body).status_code == 428
        response = http.post("/api/v1/fields", json=body, headers={"Idempotency-Key": "http-create"})
        assert response.status_code == 201, response.text
        path = response.headers["Location"]
        saved = http.get(path)
        assert saved.headers["ETag"] == response.headers["ETag"]
        assert "version" not in saved.json()["data"]
        assert http.patch(path, json={"geometry": None}, headers={"If-Match": saved.headers["ETag"]}).status_code == 422
        unclosed = deepcopy(actual_geometry)
        ring = unclosed["coordinates"][0] if unclosed["type"] == "Polygon" else unclosed["coordinates"][0][0]
        ring.pop()
        for invalid in [unclosed, {"type": "Point", "coordinates": [0, 0]},
                        {"type": "Polygon", "coordinates": [[[181, 0], [181, 1], [182, 1], [181, 0]]]}]:
            assert http.post("/api/v1/fields", json={**body, "geometry": invalid},
                             headers={"Idempotency-Key": "invalid"}).status_code == 422
        assert http.delete(path, headers={"If-Match": saved.headers["ETag"]}).status_code == 200
        assert http.get(path).status_code == 404
        assert http.get(path + "/observations").status_code == 404
