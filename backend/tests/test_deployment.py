from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from agri_data import deployment


def configuration(**changes):
    return deployment.deployment_environment({"POSTGRES_PASSWORD": "Disposable configuration probe", **changes})


def test_private_configuration_keeps_password_out_of_dsn_and_frontend():
    password = "Configuration-only $:#/@ probe"
    environment = {"POSTGRES_PASSWORD": password, "POSTGRES_USER": "user@example", "POSTGRES_DB": "test database",
                   "APP_HOST": "100.64.0.1", "API_PORT": "18084", "FRONTEND_PORT": "11084",
                   "AGRI_AUTH_MODE": "shared", "VITE_DATABASE_PASSWORD": "must not reach the frontend"}
    configured = deployment.deployment_environment(environment)
    assert configured["PGPASSWORD"] == password
    assert configured["AGRI_API_DATABASE_URL"] == "postgresql://user%40example@127.0.0.1:55432/test%20database"
    assert configured["AGRI_AUTH_MODE"] == "accounts"
    public = deployment.frontend_environment({**environment, **configured, "PGPASSFILE": "private-file"})
    assert public["VITE_API_BASE_URL"] == "http://100.64.0.1:18084"
    assert public["FRONTEND_HOST"] == "100.64.0.1"
    assert not any(key.startswith(("PG", "AGRI_", "POSTGRES_", "DB_")) for key in public)
    assert "VITE_DATABASE_PASSWORD" not in public
    assert password not in public.values()


def test_native_env_file_keeps_quoted_password_literal_and_honors_existing_environment(monkeypatch, tmp_path):
    password = "Disposable ${NOT_AN_ENV_REFERENCE}#:@ probe"
    env_file = tmp_path / "settings.env"
    env_file.write_text(f"POSTGRES_PASSWORD='{password}'\nPOSTGRES_DB=from_file\n", encoding="utf-8")
    environment = dict(deployment.os.environ)
    for name in (*configuration(), "POSTGRES_PASSWORD"):
        environment.pop(name, None)
    monkeypatch.setattr(deployment.os, "environ", environment)
    monkeypatch.setenv("POSTGRES_DB", "from_environment")
    monkeypatch.setattr("sys.argv", ["deployment", "init", "--env-file", str(env_file)])
    initialized = []
    monkeypatch.setattr(deployment, "initialize", lambda: initialized.append(dict(deployment.os.environ)))
    deployment.main()
    assert initialized[0]["PGPASSWORD"] == password
    assert initialized[0]["AGRI_API_DATABASE_NAME"] == "from_environment"


@pytest.mark.parametrize("changes", [
    {"APP_HOST": "0.0.0.0"}, {"APP_HOST": "example.com"}, {"APP_HOST": "192.168.1.2"},
    {"API_PORT": "1080"}, {"DB_PORT": "0"}, {"DB_HOST": "user:password@host"},
    {"CANONICAL_SCHEMA": "public"}, {"WORKSPACE_SCHEMA": "agri_bhumi_data"},
    {"AUTH_SESSION_SECONDS": "0"}, {"POSTGRES_PASSWORD": ""},
])
def test_unsafe_or_ambiguous_deployment_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        configuration(**changes)


def test_container_listener_does_not_relax_request_host_origin_or_account_checks(monkeypatch):
    for name, value in configuration(APP_HOST="100.64.0.1", API_PORT="18084").items():
        monkeypatch.setenv(name, value)
    calls = []
    monkeypatch.setattr(deployment.uvicorn, "run", lambda app, **options: calls.append((app, options)))
    deployment.run_api(container=True)
    app, options = calls[0]
    assert options == {"host": "0.0.0.0", "port": 8080, "proxy_headers": False}
    with TestClient(app, base_url="http://100.64.0.1:18084") as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/health", headers={"Host": "attacker.example"}).status_code == 400
        assert client.get("/api/v1/health", headers={"Origin": "http://attacker.example"}).status_code == 403
        assert app.state.account_store.settings.mode == "accounts"
    deployment.run_api()
    assert calls[1][1] == {"host": "100.64.0.1", "port": 18084, "proxy_headers": False}


def test_native_frontend_uses_public_configuration_and_explicit_ports(monkeypatch, tmp_path):
    vite = tmp_path / "node_modules" / "vite" / "bin" / "vite.js"
    vite.parent.mkdir(parents=True)
    vite.touch()
    for name, value in {"APP_HOST": "127.0.0.1", "API_PORT": "18084", "FRONTEND_PORT": "11084",
                        "POSTGRES_PASSWORD": "Never pass this to Node", "PGPASSWORD": "Nor this"}.items():
        monkeypatch.setenv(name, value)
    calls = []
    monkeypatch.setattr(deployment.shutil, "which", lambda name: "node")
    monkeypatch.setattr(deployment.subprocess, "run", lambda command, **options: calls.append((command, options)))
    deployment.frontend(tmp_path)
    assert calls[0][0] == ["node", str(vite), "build"]
    assert calls[1][0][-5:] == ["--host", "127.0.0.1", "--port", "11084", "--strictPort"]
    assert all(item[1]["env"]["VITE_API_BASE_URL"] == "http://127.0.0.1:18084" for item in calls)
    assert all("POSTGRES_PASSWORD" not in item[1]["env"] and "PGPASSWORD" not in item[1]["env"] for item in calls)


def test_worker_dispatch_does_not_reparse_deployment_arguments(monkeypatch):
    from agri_data.workspace import worker
    monkeypatch.setattr(deployment, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(deployment, "deployment_environment", lambda environ: {})
    monkeypatch.setattr("sys.argv", ["deployment", "worker", "--env-file", str(Path("settings.env"))])
    received = []
    monkeypatch.setattr(worker, "main", lambda argv: received.append(argv))
    deployment.main()
    assert received == [[]]
