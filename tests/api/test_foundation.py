import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agri_data.api.app import create_app
from agri_data.api.schemas import ProfilePatch
from agri_data.api.settings import ApiSettings


def settings(**overrides):
    overrides.setdefault("database_url", None)
    return ApiSettings(_env_file=None, **overrides)


@pytest.mark.parametrize("origin", [
    "*", "http://0.0.0.0:1080", "http://localhost:1080/path",
    "https://user:password@example.org", "http://localhost:invalid",
    "http://localhost:1080?secret=1",
])
def test_origins_require_exact_browser_addresses(origin):
    with pytest.raises(ValidationError):
        settings(allowed_origins=[origin])


def test_production_refuses_insecure_or_missing_configuration():
    with pytest.raises(ValidationError):
        settings(environment="production")
    with pytest.raises(ValidationError):
        settings(database_url="sqlite:///test.db")


def test_missing_database_is_not_ready_but_liveness_works():
    with TestClient(create_app(settings())) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_not_ready"
        assert response.headers["x-request-id"] == response.json()["error"]["request_id"]
        assert response.headers["cache-control"] == "no-store"


def test_cors_only_permits_configured_origin():
    with TestClient(create_app(settings())) as client:
        allowed = client.options("/api/v1/meta", headers={
            "Origin": "http://localhost:1080",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-Token",
        })
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:1080"
        denied = client.options("/api/v1/meta", headers={
            "Origin": "http://untrusted.invalid",
            "Access-Control-Request-Method": "POST",
        })
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers


def test_request_ids_and_errors_are_safe():
    with TestClient(create_app(settings())) as client:
        response = client.get("/missing", headers={"X-Request-ID": "<unsafe>"})
        assert response.status_code == 404
        assert response.json()["error"]["request_id"] != "<unsafe>"
        accepted = client.get("/health", headers={"X-Request-ID": "trace-123"})
        assert accepted.headers["x-request-id"] == "trace-123"


def test_streamed_body_limit_does_not_trust_content_length():
    with TestClient(create_app(settings(max_request_bytes=1024))) as client:
        response = client.post("/missing", content=iter([b"x" * 800, b"x" * 800]),
                               headers={"Origin": "http://localhost:1080"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "request_too_large"
        assert response.headers["access-control-allow-origin"] == "http://localhost:1080"


def test_internal_errors_do_not_leak_details():
    app = create_app(settings())

    @app.get("/failure")
    def failure():
        raise RuntimeError("private-database-password")

    with TestClient(app) as client:
        response = client.get("/failure")
        assert response.status_code == 500
        assert "private-database-password" not in response.text


@pytest.mark.parametrize("patch", [
    {"version": 0},
    {"version": True},
    {"version": 1, "primary_objective": "food_security"},
    {"version": 1, "farmer_category": "inferred"},
    {"version": 1, "phone": "not-a-phone"},
    {"version": 1, "owner_id": "another-user"},
])
def test_profile_rejects_invalid_and_server_owned_values(patch):
    with pytest.raises(ValidationError):
        ProfilePatch.model_validate(patch)


def test_partial_profile_preserves_omission_and_explicit_null():
    patch = ProfilePatch(version=1, name=None, farmer_category="small_marginal")
    assert patch.model_dump(exclude_unset=True) == {
        "version": 1, "name": None, "farmer_category": "small_marginal",
    }


def test_validation_envelope_uses_field_paths_and_omits_input():
    app = create_app(settings())

    @app.patch("/validate-profile")
    def validate_profile(patch: ProfilePatch):
        return patch

    with TestClient(app) as client:
        response = client.patch("/validate-profile", json={
            "version": 1, "private_input": "do-not-echo",
        })
        assert response.status_code == 422
        assert response.json()["error"]["field_errors"][0]["path"] == "/private_input"
        assert "do-not-echo" not in response.text
