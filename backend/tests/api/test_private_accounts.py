"""Real PostgreSQL account isolation; only owned disposable schemas are changed."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient
from psycopg import sql
import pytest
from shapely import force_2d
from shapely.geometry import shape

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from agri_data.api.field_writes import FieldCreate
from agri_data.api.profile import ProfilePatch
from agri_data.workspace.accounts import digest
from agri_data.workspace.formats import parse_upload, serialize_export
from agri_data.workspace.jobs import JobStore
from agri_data.workspace.settings import AccountSettings
from agri_data.workspace.store import profile_etag
from agri_data.workspace.worker import AccountWorker


ORIGIN = "http://127.0.0.1:1080"
ROOT = "/api/v1"
PASSWORD = "Disposable account integration password"


def application(fields, account_settings=None):
    return create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}),
                      fields.settings, fields.workspace.settings,
                      account_settings or AccountSettings(mode="accounts"))


@pytest.fixture
def private_app(field_store):
    return application(field_store)


def browser(app):
    return TestClient(app, base_url="http://127.0.0.1", headers={"Origin": ORIGIN})


def context(http):
    response = http.post(ROOT + "/auth/bootstrap")
    assert response.status_code == 200
    return response.json()["data"]["csrf_token"]


def credentials(http, login, *, operation="register", password=PASSWORD):
    return http.post(ROOT + "/auth/" + operation,
                     json={"login": login, "password": password},
                     headers={"X-CSRF-Token": context(http)})


def register(http, login):
    response = credentials(http, login)
    assert response.status_code == 201
    http.headers["X-CSRF-Token"] = response.json()["data"]["csrf_token"]
    http.headers["X-Account-ID"] = response.json()["data"]["user"]["id"]
    return response


def project(http):
    response = http.get(ROOT + "/workspace")
    assert response.status_code == 200
    assert response.json()["data"]["access_mode"] == "private_account"
    return response.json()["data"]["project_ids"][0]


def create_field(http, geometry, key="same-per-account-key"):
    response = http.post(ROOT + "/fields", json={
        "project_id": project(http), "name": "Private copy of real provider geometry", "geometry": geometry,
    }, headers={"Idempotency-Key": key})
    assert response.status_code == 201
    return response


def row_counts(fields):
    with fields.workspace.session() as connection:
        return [
            connection.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(table)).fetchone()["n"]
            for table in (sql.Identifier("workspace_profiles"), sql.Identifier("workspace_profile_revisions"),
                          sql.Identifier("workspace_accounts"), fields.table("projects"))
        ]


def test_private_boundary_requires_sessions_origin_csrf_and_no_owner_overrides(private_app):
    with browser(private_app) as http:
        assert http.get(ROOT + "/health").json()["data"]["contract_revision"] == "private-workspace-2"
        assert http.get(ROOT + "/auth/session").json()["data"]["user"] is None
        for path in ("/workspace", "/profile", "/fields", "/fields/guessed/observations",
                     "/imports/guessed", "/jobs/guessed", "/exports/guessed/download",
                     "/imports/guessed/download", "/fields/guessed/boundaries/guessed/original"):
            response = http.get(ROOT + path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "unauthenticated"
            assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert http.post(ROOT + "/auth/bootstrap", headers={"Origin": "https://example.com"}).status_code == 403
        http.headers.pop("Origin")
        assert http.post(ROOT + "/auth/bootstrap").status_code == 403
        http.headers["Origin"] = ORIGIN
        bootstrap = context(http)
        assert http.post(ROOT + "/auth/register", json={"login": "private-one", "password": PASSWORD},
                         headers={"X-CSRF-Token": "wrong"}).status_code == 403
        invalid = http.post(ROOT + "/auth/register", json={
            "login": "private-one", "password": "bad!pw", "workspace_id": "integration",
        }, headers={"X-CSRF-Token": bootstrap})
        assert invalid.status_code == 422 and "bad!pw" not in invalid.text
        response = register(http, "private-one")
        cookies = response.headers.get_list("Set-Cookie")
        assert any("HttpOnly" in value and "SameSite=strict" in value and "Path=/api/v1" in value
                   and "Max-Age=43200" in value for value in cookies)
        profile = http.get(ROOT + "/profile")
        headers = {"If-Match": profile.headers["ETag"]}
        csrf = http.headers.pop("X-CSRF-Token")
        assert http.patch(ROOT + "/profile", json={"name": "Denied"}, headers=headers).status_code == 403
        http.headers["X-CSRF-Token"] = csrf
        assert http.patch(ROOT + "/profile", json={"workspace_id": "integration"}, headers=headers).status_code == 422
        assert http.patch(ROOT + "/profile", json={"name": "Owned profile"}, headers=headers).status_code == 200
        preflight = http.options(ROOT + "/profile", headers={
            "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "X-CSRF-Token,If-Match",
        })
        assert preflight.status_code == 200 and preflight.headers["Access-Control-Allow-Credentials"] == "true"


def test_sessions_are_hashed_rotated_revoked_and_profiles_survive_restart(private_app, field_store):
    accounts = private_app.state.account_store
    with browser(private_app) as http:
        registered = register(http, "  Private-ONE  ")
        assert registered.json()["data"]["user"]["login"] == "private-one"
        token = http.cookies.get(accounts.session_cookie)
        profile = http.get(ROOT + "/profile")
        assert http.patch(ROOT + "/profile", json={"name": "Persisted private profile"},
                          headers={"If-Match": profile.headers["ETag"]}).status_code == 200
        with field_store.workspace.session() as connection:
            account = connection.execute("SELECT password_hash FROM workspace_accounts").fetchone()
            assert account["password_hash"].startswith("$argon2id$")
            assert connection.execute("SELECT token_hash FROM workspace_sessions WHERE user_id IS NOT NULL"
                                      ).fetchone()["token_hash"] == digest(token)
        with browser(application(field_store)) as restarted:
            restarted.cookies.update(http.cookies)
            assert restarted.get(ROOT + "/profile").json()["data"]["name"] == "Persisted private profile"
            session = restarted.get(ROOT + "/auth/session").json()["data"]
            assert session["user"] == registered.json()["data"]["user"]
            renewed = credentials(restarted, "PRIVATE-ONE", operation="login")
            assert renewed.status_code == 200
            restarted.headers["X-CSRF-Token"] = renewed.json()["data"]["csrf_token"]
            assert http.get(ROOT + "/profile").status_code == 401
            replay_cookie = dict(restarted.cookies)
            assert restarted.post(ROOT + "/auth/logout").status_code == 204
            restarted.cookies.update(replay_cookie)
            assert restarted.get(ROOT + "/profile").status_code == 401
            assert restarted.get(ROOT + "/auth/session").json()["data"]["user"] is None


def test_expired_sessions_and_disabled_accounts_fail_closed(private_app, field_store):
    with browser(private_app) as http:
        register(http, "expiry-probe")
        with field_store.workspace.session() as connection:
            connection.execute("UPDATE workspace_sessions SET expires_at=clock_timestamp()-interval '1 second'")
        assert http.get(ROOT + "/fields").status_code == 401
        login = credentials(http, "expiry-probe", operation="login")
        assert login.status_code == 200
        http.headers["X-CSRF-Token"] = login.json()["data"]["csrf_token"]
        with field_store.workspace.session() as connection:
            connection.execute("UPDATE workspace_accounts SET active=false")
        assert http.get(ROOT + "/profile").status_code == 401
        denied = credentials(http, "expiry-probe", operation="login")
        assert denied.status_code == 401 and denied.json()["error"]["code"] == "invalid_credentials"


def test_two_accounts_cannot_read_write_or_paginate_each_others_records(private_app, field_store, actual_geometry):
    shared = field_store.create(FieldCreate(project_id=field_store.settings.project_ids[0],
        name="Existing shared provider geometry copy", geometry=actual_geometry), "legacy", "legacy")
    field_store.workspace.update_profile(ProfilePatch(name="Existing shared profile"),
                                         profile_etag(field_store.workspace.get_profile()), "legacy")
    with browser(private_app) as first, browser(private_app) as second:
        register(first, "first-owner")
        register(second, "second-owner")
        assert first.get(ROOT + "/fields").json()["data"] == []
        assert first.get(ROOT + "/fields/" + shared["field_id"]).status_code == 404
        first_profile = first.get(ROOT + "/profile")
        second_profile = second.get(ROOT + "/profile")
        assert first_profile.json()["data"]["name"] is None
        assert first_profile.json()["data"]["workspace_id"] != second_profile.json()["data"]["workspace_id"]
        assert second.patch(ROOT + "/profile", json={"name": "Cross-account write"},
                            headers={"If-Match": first_profile.headers["ETag"]}).status_code == 412
        a = create_field(first, actual_geometry)
        create_field(first, actual_geometry, key="second-field")
        b = create_field(second, actual_geometry)
        field_id, own_id = a.json()["data"]["field_id"], b.json()["data"]["field_id"]
        assert field_id != own_id
        assert [row["field_id"] for row in second.get(ROOT + "/fields").json()["data"]] == [own_id]
        assert second.get(ROOT + "/profile").json()["data"]["name"] is None
        for suffix in ("", "/observations", "/observations/guessed", "/observations/guessed/evidence"):
            assert second.get(ROOT + "/fields/" + field_id + suffix).status_code == 404
        assert second.patch(ROOT + "/fields/" + field_id, json={"name": "Unauthorized"},
                            headers={"If-Match": a.headers["ETag"]}).status_code == 404
        assert second.delete(ROOT + "/fields/" + field_id,
                             headers={"If-Match": a.headers["ETag"]}).status_code == 404
        assert second.post(ROOT + "/fields", json={"project_id": project(first), "geometry": actual_geometry},
                           headers={"Idempotency-Key": "foreign-project"}).status_code == 404
        cursor = first.get(ROOT + "/fields?limit=1").json()["meta"]["next_cursor"]
        assert cursor and second.get(ROOT + "/fields", params={"limit": 1, "cursor": cursor}).status_code == 400


def test_an_account_switch_cannot_mix_existing_page_reads_or_writes(private_app):
    with browser(private_app) as first, browser(private_app) as second:
        register(first, "first-owner")
        register(second, "second-owner")
        first.cookies.update(second.cookies)
        for method, path, arguments in (
            ("GET", "/profile", {}),
            ("PATCH", "/profile", {"json": {"name": "Must not cross accounts"}}),
            ("GET", "/fields", {}),
        ):
            response = first.request(method, ROOT + path, **arguments)
            assert response.status_code == 409 and response.json()["error"]["code"] == "session_changed"
        assert second.get(ROOT + "/profile").json()["data"]["name"] is None


def test_private_kml_jobs_worker_and_downloads_preserve_owner_and_original_bytes(
    private_app, field_store, actual_geometry,
):
    accounts = private_app.state.account_store
    worker = AccountWorker(accounts)
    JobStore(field_store).heartbeat("shared-worker")
    with browser(private_app) as first, browser(private_app) as second:
        register(first, "first-owner")
        register(second, "second-owner")
        capabilities = {row["capability_id"]: row["state"]
                        for row in first.get(ROOT + "/workspace").json()["data"]["capabilities"]}
        assert capabilities["imports"] == "blocked"
        worker.heartbeat("private-worker")
        capabilities = {row["capability_id"]: row["state"]
                        for row in second.get(ROOT + "/workspace").json()["data"]["capabilities"]}
        assert capabilities["imports"] == "ready"
        content = serialize_export([{"type": "Feature", "id": "private-geometry-probe",
            "geometry": actual_geometry, "properties": {"name": "Real geometry copy & <label>"}}], "kml")
        query = {"filename": 'private "quoted".kml', "project_id": project(first), "source_namespace": "drawn-probe"}
        headers = {"Content-Type": "application/vnd.google-earth.kml+xml", "Idempotency-Key": "upload"}
        assert second.post(ROOT + "/imports", params=query, content=content, headers=headers).status_code == 404
        submitted = first.post(ROOT + "/imports", params=query, content=content, headers=headers)
        assert submitted.status_code == 202
        job = submitted.json()["data"]
        original_import = ROOT + "/imports/" + job["resource_id"] + "/download"
        assert first.get(original_import).content == content
        assert second.get(original_import).status_code == 404
        assert first.get(ROOT + "/fields").json()["data"] == []
        assert worker.run_once("private-worker")
        assert first.get(ROOT + "/jobs/" + job["job_id"]).json()["data"]["status"] == "succeeded"
        info = first.get(ROOT + "/imports/" + job["resource_id"]).json()["data"]
        assert first.get(ROOT + "/fields").json()["data"] == []
        for path in ("/jobs/" + job["job_id"], "/imports/" + info["import_id"]):
            assert second.get(ROOT + path).status_code == 404
        selection = {"preview_hash": info["preview_hash"],
                     "candidate_ids": [row["candidate_id"] for row in info["candidates"]]}
        confirmed = first.post(ROOT + "/imports/" + info["import_id"] + "/confirm",
                               json=selection, headers={"Idempotency-Key": "confirm"})
        assert confirmed.status_code == 202 and worker.run_once("private-worker")
        field = first.get(ROOT + "/fields").json()["data"][0]
        original_path = ROOT + "/fields/" + field["field_id"] + "/boundaries/" + field["selected_boundary_id"] + "/original"
        original = first.get(original_path)
        assert original.status_code == 200 and original.content == content
        assert original.headers["ETag"] == f'"sha256:{info["sha256"]}"'
        assert original.headers["Content-Disposition"] == f'attachment; filename="original_{info["sha256"]}.kml"'
        assert second.get(original_path).status_code == 404
        assert shape(field["geometry"]).equals_exact(force_2d(shape(actual_geometry)), 1e-12)
        assert first.get(ROOT + "/fields/" + field["field_id"] + "/observations").json()["data"] == []
        account = accounts.session(first.cookies.get(accounts.session_cookie))
        with field_store.workspace.session() as connection:
            asset = connection.execute(
                "SELECT original_bytes FROM workspace_assets WHERE workspace_id=%s AND sha256=%s",
                (account["workspace_id"], info["sha256"]),
            ).fetchone()
            assert bytes(asset["original_bytes"]) == content
        export_body = {"format": "kml", "fields": [{
            "field_id": field["field_id"], "boundary_id": field["selected_boundary_id"]}]}
        assert second.post(ROOT + "/exports", json=export_body,
                           headers={"Idempotency-Key": "export"}).status_code == 404
        exported = first.post(ROOT + "/exports", json=export_body,
                              headers={"Idempotency-Key": "export"}).json()["data"]
        assert worker.run_once("private-worker")
        download_path = ROOT + "/exports/" + exported["resource_id"] + "/download"
        assert second.get(download_path).status_code == 404
        download = first.get(download_path)
        assert download.status_code == 200
        parsed, rejected = parse_upload(download.content, "private.kml", "readback", "probe")
        assert not rejected and shape(parsed[0]["original_geometry"]).equals_exact(shape(actual_geometry), 1e-12)
        assert second.get(ROOT + "/fields").json()["data"] == []
        assert second.post(ROOT + "/imports/" + info["import_id"] + "/confirm", json=selection,
                           headers={"Idempotency-Key": "foreign-confirm"}).status_code == 404
        current = first.get(ROOT + "/fields/" + field["field_id"])
        assert first.delete(ROOT + "/fields/" + field["field_id"],
                            headers={"If-Match": current.headers["ETag"]}).status_code == 200
        assert first.get(original_path).status_code == 404
        assert first.get(original_import).content == content


def test_registration_rolls_back_profile_project_and_account_on_database_failure(private_app, field_store):
    before = row_counts(field_store)
    with field_store.workspace.session() as connection:
        connection.execute("ALTER TABLE workspace_accounts ADD CONSTRAINT registration_probe CHECK(login <> 'atomic-probe')")
    with browser(private_app) as http:
        failed = credentials(http, "atomic-probe")
        assert failed.status_code == 503
        assert row_counts(field_store) == before
        assert http.get(ROOT + "/auth/session").json()["data"]["user"] is None
        with field_store.workspace.session() as connection:
            connection.execute("ALTER TABLE workspace_accounts DROP CONSTRAINT registration_probe")
        register(http, "atomic-probe")
        assert row_counts(field_store) == [value + 1 for value in before]


def test_worker_discovers_new_accounts_without_processing_disabled_owners(private_app, field_store, actual_geometry):
    worker = AccountWorker(private_app.state.account_store)
    worker.heartbeat("already-running-worker")
    content = serialize_export([{"type": "Feature", "id": "source-copy",
        "geometry": actual_geometry, "properties": {"name": "Actual geometry copy"}}], "kml")
    headers = {"Content-Type": "application/vnd.google-earth.kml+xml", "Idempotency-Key": "new-account"}
    with browser(private_app) as first, browser(private_app) as second:
        owner = register(first, "disabled-owner").json()["data"]["user"]["id"]
        query = {"filename": "copy.kml", "project_id": project(first), "source_namespace": "new-owner"}
        first_job = first.post(ROOT + "/imports", params=query, content=content, headers=headers).json()["data"]
        with field_store.workspace.session() as connection:
            connection.execute("UPDATE workspace_accounts SET active=false WHERE user_id=%s", (owner,))
        register(second, "new-owner")
        query["project_id"] = project(second)
        second_job = second.post(ROOT + "/imports", params=query, content=content, headers=headers).json()["data"]
        assert worker.run_once("already-running-worker")
        assert second.get(ROOT + "/jobs/" + second_job["job_id"]).json()["data"]["status"] == "succeeded"
        assert not worker.run_once("already-running-worker")
        with field_store.workspace.session() as connection:
            assert connection.execute("SELECT status FROM workspace_jobs WHERE job_id=%s",
                                      (first_job["job_id"],)).fetchone()["status"] == "queued"
            connection.execute("UPDATE workspace_accounts SET active=true WHERE user_id=%s", (owner,))
        assert worker.run_once("already-running-worker")
        assert first.get(ROOT + "/jobs/" + first_job["job_id"]).json()["data"]["status"] == "succeeded"


def test_concurrent_duplicate_registration_creates_one_private_scope(private_app, field_store):
    before = row_counts(field_store)
    with browser(private_app) as first, browser(private_app) as second:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda http: credentials(http, "same-login"), (first, second)))
        assert sorted(response.status_code for response in results) == [201, 409]
        assert row_counts(field_store) == [value + 1 for value in before]


def test_authentication_limits_persist_across_app_restart_and_expired_bootstraps_fail(field_store):
    limited = AccountSettings(mode="accounts", login_attempt_limit=2)
    app = application(field_store, limited)
    with browser(app) as http:
        register(http, "limited-owner")
        for _ in range(2):
            denied = credentials(http, "limited-owner", operation="login", password="incorrect")
            assert denied.status_code == 401 and denied.json()["error"]["code"] == "invalid_credentials"
        with browser(application(field_store, limited)) as restarted:
            denied = credentials(restarted, "LIMITED-OWNER", operation="login")
            assert denied.status_code == 429 and denied.headers["Retry-After"] == "900"
        bootstrap = context(http)
        with field_store.workspace.session() as connection:
            connection.execute(
                "UPDATE workspace_sessions SET expires_at=clock_timestamp()-interval '1 second' WHERE user_id IS NULL")
        denied = http.post(ROOT + "/auth/register", json={"login": "expired-bootstrap", "password": PASSWORD},
                           headers={"X-CSRF-Token": bootstrap})
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "csrf_expired"


def test_account_mode_cannot_fall_back_to_shared_or_a_different_canonical_schema(private_app, field_store):
    with pytest.raises(ValueError):
        create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}), account_settings=AccountSettings(mode="accounts"))
    with pytest.raises(ValueError):
        create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": "http://localhost:1080"}),
                   field_store.settings, field_store.workspace.settings, AccountSettings(mode="accounts"))
    with browser(private_app) as http:
        register(http, "schema-owner")
        token = http.cookies.get(private_app.state.account_store.session_cookie)
        other = create_app(Settings.from_env({"AGRI_ALLOWED_ORIGINS": ORIGIN}),
                           replace(field_store.settings, schema="agri_other_schema"),
                           field_store.workspace.settings, AccountSettings(mode="accounts"))
        with browser(other) as wrong_schema:
            wrong_schema.cookies.set(other.state.account_store.session_cookie, token)
            assert wrong_schema.get(ROOT + "/fields").status_code == 401
