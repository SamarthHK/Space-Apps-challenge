from contextlib import contextmanager
import os
import secrets
import socket
import subprocess
import sys
import time

import httpx
import pytest

from agri_data.services.identity import create_account


@contextmanager
def running_api(settings):
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    env = os.environ.copy()
    env.update({
        "AGRI_ENVIRONMENT": "test",
        "AGRI_DATABASE_URL": settings.database_url.get_secret_value(),
        "AGRI_DATABASE_SCHEMA": settings.database_schema,
    })
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agri_data.api.app:create_app",
         "--factory", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 15
        with httpx.Client(base_url=origin, timeout=2, trust_env=False) as client:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("API process exited before readiness")
                try:
                    if client.get("/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("Real HTTP API did not become ready")
            yield client
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_login_profile_commit_and_session_survive_api_restart(database_settings):
    password = secrets.token_urlsafe(24)
    create_account(database_settings, "http-acceptance", password)
    browser_origin = "http://localhost:1080"
    with running_api(database_settings) as first:
        csrf = first.get("/api/v1/auth/csrf", headers={"Origin": browser_origin})
        assert csrf.status_code == 200
        session = first.post("/api/v1/auth/session", json={
            "login": "http-acceptance", "password": password,
        }, headers={"Origin": browser_origin, "X-CSRF-Token": csrf.json()["csrf_token"]})
        assert session.status_code == 200
        assert session.headers["access-control-allow-origin"] == browser_origin
        saved = first.patch("/api/v1/me/profile", json={
            "version": 1, "preferred_language": "kn",
        }, headers={
            "Origin": browser_origin, "X-CSRF-Token": session.json()["csrf_token"],
        })
        assert saved.status_code == 200
        cookies = first.cookies
    with running_api(database_settings) as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get("/api/v1/auth/session").status_code == 200
        assert restarted.get("/api/v1/me/profile").json() == saved.json()
        response = restarted.delete("/api/v1/auth/session", headers={
            "Origin": browser_origin, "X-CSRF-Token": session.json()["csrf_token"],
        })
        assert response.status_code == 204
        assert restarted.get("/api/v1/me/profile").status_code == 401
