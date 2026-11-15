"""HTTP/configuration tests; no fabricated agricultural records or provider mocks."""

import json
import os
import socket
import subprocess
import sys
import time

import pytest
import requests

from agri_data.api.app import create_app
from agri_data.api.config import Settings
from fastapi.testclient import TestClient


def settings(**changes):
    return Settings.from_env({"AGRI_ALLOWED_ORIGINS": "http://localhost:1080", **changes})


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.1", "8.8.8.8", "example.com", "100.128.0.1"])
def test_public_wildcard_and_untrusted_binds_are_rejected(host):
    with pytest.raises(ValueError):
        settings(AGRI_API_HOST=host)


@pytest.mark.parametrize("url", [
    "", "*", "null", "http://localhost:1080/path", "http://user:secret@localhost",
    "http://localhost?x=1", "http://localhost#x", "ftp://localhost", "http://0.0.0.0:1080",
    "http://example.com", "http://localhost:0", "http://localhost:99999", "http://localhost:abc",
])
def test_ambiguous_or_unsafe_frontend_origins_fail_startup(url):
    with pytest.raises(ValueError):
        settings(AGRI_ALLOWED_ORIGINS=url)


@pytest.mark.parametrize("port", ["0", "-1", "65536", "not-a-port"])
def test_invalid_ports_fail_startup(port):
    with pytest.raises(ValueError):
        settings(AGRI_API_PORT=port)


def test_tailnet_and_loopback_are_supported_without_embedded_machine_address():
    assert settings(AGRI_API_HOST="100.64.0.1").bind_host == "100.64.0.1"
    assert settings().port == 8000
    assert settings(AGRI_ALLOWED_ORIGINS="http://localhost:1080/,http://localhost:1080").allowed_origins == (
        "http://localhost:1080",
    )


@pytest.fixture(scope="module")
def server():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    environment = {
        **os.environ, "AGRI_API_HOST": "127.0.0.1", "AGRI_API_PORT": str(port),
        "AGRI_ALLOWED_ORIGINS": "http://localhost:1080",
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "agri_data.api"], env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    root = f"http://127.0.0.1:{port}/api/v1"
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail("API exited before readiness")
            try:
                if requests.get(root + "/health", timeout=0.2).status_code == 200:
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.05)
        else:
            pytest.fail("API did not become ready")
        yield root
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_live_health_and_workspace_are_honest_and_share_response_contract(server):
    response = requests.get(server + "/health", headers={"X-Request-ID": "audit-123"}, timeout=2)
    assert response.status_code == 200
    assert response.json()["meta"] == {"request_id": "audit-123", "api_version": "v1"}
    assert response.headers["X-Request-ID"] == "audit-123"
    assert response.headers["Cache-Control"] == "no-store"
    workspace = requests.get(server + "/workspace", timeout=2).json()["data"]
    assert workspace["access_mode"] == "shared_trusted_network"
    assert workspace["project_ids"] == []
    assert all(item["state"] == ("blocked" if item["capability_id"] in (
        "fields", "observations", "profile", "field_writes", "jobs", "imports", "exports", "boundary_originals")
                                else "not_implemented") for item in workspace["capabilities"])
    assert "user_id" not in workspace and "token" not in workspace


def test_cors_allows_only_explicit_frontend_and_no_cookies(server):
    response = requests.get(server + "/health", headers={"Origin": "http://localhost:1080"}, timeout=2)
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:1080"
    assert "Access-Control-Allow-Credentials" not in response.headers
    rejected = requests.get(server + "/health", headers={"Origin": "https://example.com"}, timeout=2)
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "origin_not_allowed"
    assert "Access-Control-Allow-Origin" not in rejected.headers
    preflight = requests.options(server + "/workspace", headers={
        "Origin": "http://localhost:1080", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Request-ID",
    }, timeout=2)
    assert preflight.status_code == 200


def test_unknown_routes_methods_hosts_and_request_ids_are_handled(server):
    missing = requests.get(server + "/missing", timeout=2)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    write = requests.post(server + "/workspace", json={}, headers={"Origin": "http://localhost:1080"}, timeout=2)
    assert write.status_code == 405
    assert write.json()["error"]["code"] == "method_not_allowed"
    host = requests.get(server + "/health", headers={"Host": "example.com"}, timeout=2)
    assert host.status_code == 400
    invalid_id = requests.get(server + "/health", headers={"X-Request-ID": "x" * 65}, timeout=2)
    assert len(invalid_id.headers["X-Request-ID"]) == 32


def test_openapi_export_is_deterministic_and_matches_live_routes(server, tmp_path):
    live = requests.get(server + "/openapi.json", timeout=2).json()
    assert live == create_app(settings()).openapi()
    operations = {operation["operationId"] for path in live["paths"].values() for operation in path.values()}
    assert operations == {"getHealth", "getWorkspace", "listFields", "getField", "listObservations",
                          "getObservation", "listObservationEvidence", "getProfile", "updateProfile",
                          "createField", "updateField", "archiveField", "getJob",
                          "createBoundaryImport", "getBoundaryImport", "confirmBoundaryImport",
                          "createExport", "downloadExport", "getSession", "createSignInContext",
                          "registerAccount", "loginAccount", "logoutAccount",
                          "downloadBoundaryImport", "downloadBoundaryOriginal"}
    output = tmp_path / "openapi.json"
    result = subprocess.run(
        [sys.executable, "-m", "agri_data.api", "--export-openapi", str(output)],
        env={**os.environ, "AGRI_ALLOWED_ORIGINS": "http://localhost:1080"},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == live
    assert b"\r\n" not in output.read_bytes(), "Contract checksums must not depend on checkout platform"


def test_unexpected_failures_are_redacted_and_readable_by_allowed_frontend():
    app = create_app(settings())

    @app.get("/broken")
    def broken():
        raise RuntimeError("internal-secret-database-path")

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/broken", headers={"Origin": "http://localhost:1080"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "internal-secret" not in response.text
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:1080"


def test_unconfigured_data_is_not_an_empty_success_and_queries_are_validated(server):
    response = requests.get(server + "/fields", timeout=3)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "data_unavailable"
    for query in ["limit=0", "limit=201", "limit=word"]:
        invalid = requests.get(server + "/fields?" + query, timeout=3)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "validation_error"
