from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import os
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from agri_data.api.profile import ProfilePatch
from agri_data.workspace.errors import WorkspaceError, WorkspaceUnavailable
from agri_data.workspace.store import WorkspaceStore, profile_etag
from agri_data.workspace.settings import WorkspaceSettings


ORIGIN = "http://127.0.0.1:1080"


def client(store, prepared=None):
    app = create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}), prepared, store.settings)
    return TestClient(app, base_url="http://127.0.0.1", headers={"Origin": ORIGIN})


def test_shared_profile_persists_with_null_semantics_and_revision(workspace_store):
    with client(workspace_store) as http:
        initial = http.get("/api/v1/profile")
        assert initial.status_code == 200
        assert initial.json()["data"]["name"] is None
        assert "Set-Cookie" not in initial.headers
        changed = http.patch("/api/v1/profile", json={"name": "Shared integration workspace",
            "farmer_category": "small_marginal", "preferred_language": "kn"},
            headers={"If-Match": initial.headers["ETag"]})
        assert changed.status_code == 200, changed.text
        assert changed.json()["data"]["version"] == 2
        cleared = http.patch("/api/v1/profile", json={"name": None},
                             headers={"If-Match": changed.headers["ETag"]})
        assert cleared.status_code == 200
        assert cleared.json()["data"]["name"] is None
        assert cleared.json()["data"]["preferred_language"] == "kn"
    with client(workspace_store) as other:
        assert other.get("/api/v1/profile").json()["data"]["version"] == 3
    with workspace_store.session() as connection:
        rows = connection.execute(
            "SELECT version,snapshot FROM workspace_profile_revisions ORDER BY version").fetchall()
        assert [row["version"] for row in rows] == [1, 2, 3]
        assert rows[1]["snapshot"]["name"] == "Shared integration workspace"
    settings = workspace_store.settings
    environment = dict(os.environ, AGRI_WORKSPACE_DATABASE_URL=settings.dsn,
        AGRI_WORKSPACE_DATABASE_NAME=settings.database, AGRI_WORKSPACE_DATABASE_USER=settings.user,
        AGRI_WORKSPACE_SCHEMA=settings.schema, AGRI_WORKSPACE_ID=settings.workspace_id)
    result = subprocess.run([sys.executable, "-c",
        "from agri_data.workspace.settings import WorkspaceSettings;"
        "from agri_data.workspace.store import WorkspaceStore;"
        "print(WorkspaceStore(WorkspaceSettings.from_env()).get_profile()['version'])"],
        env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3"


@pytest.mark.parametrize("body", [{}, {"version": 1}, {"workspace_id": "other"},
    {"phone": "invalid"}, {"farmer_category": "inferred"}, {"name": "x" * 201}])
def test_invalid_profile_changes_are_rejected(workspace_store, body):
    with client(workspace_store) as http:
        etag = http.get("/api/v1/profile").headers["ETag"]
        response = http.patch("/api/v1/profile", json=body, headers={"If-Match": etag})
        assert response.status_code == 422
        assert response.json()["error"]["details"]
    assert workspace_store.get_profile()["version"] == 1


def test_missing_stale_and_malformed_preconditions(workspace_store):
    with client(workspace_store) as http:
        body = {"name": "An explicit workspace label"}
        assert http.patch("/api/v1/profile", json=body).status_code == 428
        for value in ['*', 'W/"profile:integration:1"', '"wrong"', '"profile:integration:1","other"']:
            assert http.patch("/api/v1/profile", json=body, headers={"If-Match": value}).status_code == 400
        response = http.patch("/api/v1/profile", json=body,
                              headers={"If-Match": '"profile:other:1"'})
        assert response.status_code == 412
        assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
        assert "ETag" in response.headers["Access-Control-Expose-Headers"]


def test_two_writers_cannot_overwrite_each_other(workspace_store):
    etag = profile_etag(workspace_store.get_profile())
    def update(name):
        try:
            workspace_store.update_profile(ProfilePatch(name=name), etag, "concurrency")
            return 200
        except WorkspaceError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, ["first change", "second change"])) == [200, 412]
    assert workspace_store.get_profile()["version"] == 2
    with workspace_store.session() as connection:
        assert connection.execute("SELECT count(*) AS n FROM workspace_profile_revisions").fetchone()["n"] == 2


def test_revision_failure_rolls_back_profile_update(workspace_store):
    with workspace_store.session() as connection:
        connection.execute(
            "ALTER TABLE workspace_profile_revisions ADD CONSTRAINT rollback_probe "
            "CHECK (request_id <> 'reject')"
        )
    etag = profile_etag(workspace_store.get_profile())
    with pytest.raises(WorkspaceUnavailable):
        workspace_store.update_profile(ProfilePatch(name="Must roll back"), etag, "reject")
    assert workspace_store.get_profile()["version"] == 1
    assert workspace_store.get_profile()["name"] is None


def test_origin_preflight_and_data_reads_stay_independent(workspace_store, prepared_settings):
    with client(workspace_store, prepared_settings) as http:
        preflight = http.options("/api/v1/profile", headers={
            "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "content-type,if-match"})
        assert preflight.status_code == 200
        assert "Access-Control-Allow-Credentials" not in preflight.headers
        assert http.patch("/api/v1/profile", json={"name": "denied"},
                          headers={"Origin": "http://untrusted.invalid"}).status_code == 403
        http.headers.pop("Origin")
        assert http.patch("/api/v1/profile", json={"name": "denied"}).status_code == 403
        assert http.get("/api/v1/fields").status_code == 200
        capabilities = http.get("/api/v1/workspace").json()["data"]["capabilities"]
        assert next(row for row in capabilities if row["capability_id"] == "profile")["state"] == "ready"
        assert http.get("/api/v1/auth/session").status_code == 404


def test_setup_is_explicit_and_migrations_detect_drift(workspace_store):
    missing = WorkspaceStore(replace(workspace_store.settings, workspace_id="not-provisioned"))
    assert not missing.ready()
    with pytest.raises(WorkspaceUnavailable):
        missing.get_profile()
    workspace_store.provision()
    assert workspace_store.get_profile()["version"] == 1
    with workspace_store.session() as connection:
        connection.execute("UPDATE workspace_migrations SET sha256='changed'")
    assert not workspace_store.ready()
    with pytest.raises(WorkspaceUnavailable):
        workspace_store.migrate()


def test_workspace_configuration_cannot_fall_back():
    assert WorkspaceSettings.from_env({}) is None
    with pytest.raises(ValueError):
        WorkspaceSettings.from_env({"AGRI_WORKSPACE_ID": "only-one-setting"})
