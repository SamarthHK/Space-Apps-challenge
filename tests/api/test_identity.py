from concurrent.futures import ThreadPoolExecutor
import secrets

from fastapi.testclient import TestClient
import pytest

from agri_data.api.app import create_app
from agri_data.api.identity import SESSION_COOKIE, CONTEXT_COOKIE
from agri_data.services.database import connect
from agri_data.services.errors import ServiceError
from agri_data.services.identity import create_account, digest, revoke_user_sessions

ORIGIN = "http://localhost:1080"


@pytest.fixture
def account(database_settings):
    password = secrets.token_urlsafe(24)
    user_id = create_account(database_settings, "acceptance-user", password)
    return {"id": user_id, "login": "acceptance-user", "password": password}


def sign_in(client, account, origin=ORIGIN):
    csrf = client.get("/api/v1/auth/csrf", headers={"Origin": origin})
    assert csrf.status_code == 200, csrf.text
    return client.post("/api/v1/auth/session", json={
        "login": account["login"], "password": account["password"],
    }, headers={"Origin": origin, "X-CSRF-Token": csrf.json()["csrf_token"]})


def mutation_headers(session, origin=ORIGIN):
    return {"Origin": origin, "X-CSRF-Token": session["csrf_token"]}


def test_session_lifecycle_cookie_security_hashing_and_restart(database_settings, account):
    with TestClient(create_app(database_settings)) as first:
        assert first.get("/api/v1/me/profile").status_code == 401
        signed = sign_in(first, account)
        assert signed.status_code == 200
        session = signed.json()
        assert session["user"]["id"] == account["id"]
        cookie_headers = signed.headers.get_list("set-cookie")
        assert any("HttpOnly" in header and "SameSite=lax" in header for header in cookie_headers)
        token = first.cookies.get(SESSION_COOKIE)
        assert account["password"] not in signed.text
        with connect(database_settings) as connection:
            row = connection.execute("SELECT password_hash FROM users").fetchone()
            assert row["password_hash"].startswith("$argon2id$")
            assert account["password"] not in row["password_hash"]
            stored = connection.execute("SELECT token_hash FROM auth_sessions").fetchone()
            assert stored["token_hash"] == digest(token)
            assert token != stored["token_hash"]
        with TestClient(create_app(database_settings)) as second:
            second.cookies.set(SESSION_COOKIE, token)
            assert second.get("/api/v1/auth/session").json() == session
            response = second.delete("/api/v1/auth/session", headers=mutation_headers(session))
            assert response.status_code == 204 and not response.content
        assert first.get("/api/v1/auth/session").status_code == 401


def test_login_requires_matching_one_use_csrf_and_origin(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        body = {"login": account["login"], "password": account["password"]}
        assert client.post("/api/v1/auth/session", json=body).status_code == 403
        assert client.get("/api/v1/auth/csrf", headers={"Origin": "http://evil.invalid"}).status_code == 403
        csrf = client.get("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()["csrf_token"]
        context = client.cookies.get(CONTEXT_COOKIE)
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
        assert client.post("/api/v1/auth/session", json=body, headers={
            **headers, "Origin": "http://evil.invalid",
        }).status_code == 403
        assert client.post("/api/v1/auth/session", json=body, headers={
            **headers, "X-CSRF-Token": "wrong",
        }).status_code == 403
        assert client.post("/api/v1/auth/session", json=body, headers=headers).status_code == 200
        client.cookies.set(CONTEXT_COOKIE, context)
        assert client.post("/api/v1/auth/session", json=body, headers=headers).status_code == 403


def test_rotation_retires_previous_authenticated_cookie(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        assert sign_in(client, account).status_code == 200
        old = client.cookies.get(SESSION_COOKIE)
        assert sign_in(client, account).status_code == 200
        assert old != client.cookies.get(SESSION_COOKIE)
        with TestClient(create_app(database_settings)) as replay:
            replay.cookies.set(SESSION_COOKIE, old)
            assert replay.get("/api/v1/me/profile").status_code == 401


@pytest.mark.parametrize("state", ["expired", "revoked", "disabled"])
def test_expired_revoked_and_disabled_sessions_are_denied(database_settings, account, state):
    with TestClient(create_app(database_settings)) as client:
        signed = sign_in(client, account).json()
        token = client.cookies.get(SESSION_COOKIE)
        with connect(database_settings) as connection:
            if state == "expired":
                connection.execute(
                    "UPDATE auth_sessions SET created_at=clock_timestamp()-interval '2 hours', "
                    "expires_at=clock_timestamp()-interval '1 hour' WHERE token_hash=%s",
                    (digest(token),),
                )
            elif state == "revoked":
                connection.execute("UPDATE auth_sessions SET revoked_at=clock_timestamp()")
            else:
                connection.execute("UPDATE users SET active=false")
        assert client.get("/api/v1/auth/session").status_code == 401
        assert client.patch("/api/v1/me/profile", json={
            "version": 1, "preferred_language": "kn",
        }, headers=mutation_headers(signed)).status_code == 401


def test_invalid_login_errors_match_and_limits_survive_app_restart(database_settings, account):
    settings = database_settings.model_copy(update={"login_attempt_limit": 2})
    with TestClient(create_app(settings)) as client:
        csrf = client.get("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()["csrf_token"]
        context = client.cookies.get(CONTEXT_COOKIE)
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
        errors = []
        for login in (account["login"], "nonexistent-user"):
            response = client.post("/api/v1/auth/session", json={
                "login": login, "password": "incorrect-password",
            }, headers=headers)
            assert response.status_code == 401
            errors.append(response.json()["error"]["message"])
        assert errors[0] == errors[1]
    with TestClient(create_app(settings)) as restarted:
        restarted.cookies.set(CONTEXT_COOKIE, context)
        response = restarted.post("/api/v1/auth/session", json={
            "login": account["login"], "password": account["password"],
        }, headers=headers)
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0


def test_profile_roundtrip_owner_isolation_nulls_and_history(database_settings, account):
    other = {"login": "acceptance-other", "password": secrets.token_urlsafe(24)}
    create_account(database_settings, other["login"], other["password"])
    with TestClient(create_app(database_settings)) as first, TestClient(create_app(database_settings)) as second:
        signed = sign_in(first, account).json()
        assert sign_in(second, other).status_code == 200
        before = first.get("/api/v1/me/profile").json()
        assert before["name"] is None
        assert "user_id" not in before
        response = first.patch("/api/v1/me/profile", json={
            "version": before["version"], "preferred_language": "kn",
            "farmer_category": "small_marginal", "primary_objective": "household_security",
        }, headers=mutation_headers(signed))
        assert response.status_code == 200
        assert response.json()["version"] == 2
        assert response.json()["farmer_category"] == "small_marginal"
        assert second.get("/api/v1/me/profile").json()["preferred_language"] is None
        cleared = first.patch("/api/v1/me/profile", json={
            "version": 2, "preferred_language": None,
        }, headers=mutation_headers(signed))
        assert cleared.status_code == 200
        assert cleared.json()["preferred_language"] is None
        assert cleared.json()["primary_objective"] == "household_security"
        with connect(database_settings) as connection:
            revisions = connection.execute(
                "SELECT version FROM profile_revisions WHERE profile_id=%s ORDER BY version",
                (before["id"],),
            ).fetchall()
            assert [row["version"] for row in revisions] == [1, 2, 3]


def test_profile_rejects_unknown_fields_query_and_csrf(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        signed = sign_in(client, account).json()
        headers = mutation_headers(signed)
        assert client.patch("/api/v1/me/profile", json={
            "version": 1, "preferred_language": "kn",
        }).status_code == 403
        assert client.patch("/api/v1/me/profile", json={
            "version": 1, "user_id": account["id"],
        }, headers=headers).status_code == 422
        assert client.get("/api/v1/me/profile?user_id=" + account["id"]).status_code == 422
        assert client.patch("/api/v1/me/profile", json={"version": 1}, headers=headers).status_code == 422


def test_simultaneous_updates_have_one_winner(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        signed = sign_in(client, account).json()
        token = client.cookies.get(SESSION_COOKIE)

    def save(language):
        with TestClient(create_app(database_settings)) as peer:
            peer.cookies.set(SESSION_COOKIE, token)
            return peer.patch("/api/v1/me/profile", json={
                "version": 1, "preferred_language": language,
            }, headers=mutation_headers(signed)).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["en", "kn"])) == [200, 409]


def test_profile_and_revision_are_atomic_on_database_failure(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        signed = sign_in(client, account).json()
        with connect(database_settings) as connection:
            connection.execute("DROP TABLE profile_revisions")
        response = client.patch("/api/v1/me/profile", json={
            "version": 1, "preferred_language": "kn",
        }, headers=mutation_headers(signed))
        assert response.status_code == 503
        unchanged = client.get("/api/v1/me/profile").json()
        assert unchanged["version"] == 1 and unchanged["preferred_language"] is None
        assert "profile_revisions" not in response.text


def test_provisioning_and_admin_revocation(database_settings, account):
    with pytest.raises(ServiceError):
        create_account(database_settings, account["login"].upper(), account["password"])
    with pytest.raises(ValueError):
        create_account(database_settings, "short-password", "short")
    with TestClient(create_app(database_settings)) as client:
        assert sign_in(client, account).status_code == 200
        assert revoke_user_sessions(database_settings, account["login"]) == 1
        assert client.get("/api/v1/me/profile").status_code == 401


def test_production_cookie_is_secure(database_settings, account):
    settings = database_settings.model_copy(update={
        "environment": "production", "cookie_secure": True,
        "allowed_origins": ["https://frontend.example.test"],
    })
    with TestClient(create_app(settings), base_url="https://api.example.test") as client:
        response = sign_in(client, account, "https://frontend.example.test")
        assert response.status_code == 200
        assert all("Secure" in value for value in response.headers.get_list("set-cookie"))
        assert client.get("/api/v1/auth/session").status_code == 200


def test_expired_bootstrap_and_wrong_browser_context_are_rejected(database_settings, account):
    with TestClient(create_app(database_settings)) as first, TestClient(create_app(database_settings)) as second:
        first_csrf = first.get("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()["csrf_token"]
        second.get("/api/v1/auth/csrf", headers={"Origin": ORIGIN})
        body = {"login": account["login"], "password": account["password"]}
        headers = {"Origin": ORIGIN, "X-CSRF-Token": first_csrf}
        assert second.post("/api/v1/auth/session", json=body, headers=headers).status_code == 403
        with connect(database_settings) as connection:
            connection.execute(
                "UPDATE auth_sessions SET created_at=clock_timestamp()-interval '2 hours', "
                "expires_at=clock_timestamp()-interval '1 hour' WHERE user_id IS NULL"
            )
        assert first.post("/api/v1/auth/session", json=body, headers=headers).status_code == 403


def test_profile_origin_and_schema_never_echo_password(database_settings, account):
    with TestClient(create_app(database_settings)) as client:
        signed = sign_in(client, account).json()
        response = client.patch("/api/v1/me/profile", json={
            "version": 1, "preferred_language": "kn",
        }, headers=mutation_headers(signed, "http://untrusted.invalid"))
        assert response.status_code == 403
        malformed = client.post("/api/v1/auth/session", json={
            "login": account["login"], "password": account["password"], "extra": True,
        })
        assert malformed.status_code == 422
        assert account["password"] not in malformed.text
