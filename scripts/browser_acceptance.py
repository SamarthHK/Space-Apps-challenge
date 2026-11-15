"""Run the production frontend against a separate real API and acceptance schema."""

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx
from psycopg import sql

from agri_data.api.settings import ApiSettings
from agri_data.services.database import connect, migrate
from agri_data.services.identity import create_account


def require_free_ports(ports):
    for port in ports:
        with socket.socket() as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise RuntimeError(
                    f"Acceptance port {port} is unavailable; leave existing services untouched"
                ) from error


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", type=Path, default=root / ".local" / "frontend")
    args = parser.parse_args()
    frontend = args.frontend.resolve()
    if not (frontend / "playwright.config.js").is_file():
        parser.error("Provide the integrated frontend worktree")
    settings = ApiSettings()
    if not settings.database_url:
        parser.error("Configure real PostgreSQL first")
    schema = "acceptance_browser_" + uuid4().hex
    settings = settings.model_copy(update={"database_schema": schema})
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        parser.error("npm is required")
    require_free_ports((18080, 11080))
    process = None
    try:
        migrate(settings)
        password = secrets.token_urlsafe(32)
        create_account(settings, "browser-acceptance", password)
        env = os.environ.copy()
        env.update({
            "AGRI_ENVIRONMENT": "test",
            "AGRI_DATABASE_URL": settings.database_url.get_secret_value(),
            "AGRI_DATABASE_SCHEMA": schema,
            "AGRI_ALLOWED_ORIGINS": json.dumps(["http://127.0.0.1:11080"]),
            "AGRI_LOGIN_ATTEMPT_LIMIT": "100",
            "AGRI_TEST_LOGIN": "browser-acceptance",
            "AGRI_TEST_PASSWORD": password,
            "VITE_API_BASE_URL": "http://127.0.0.1:18080",
            "PLAYWRIGHT_BROWSERS_PATH": str(root / ".local" / "playwright"),
        })
        subprocess.run([npm, "run", "build"], cwd=frontend, env=env, check=True)
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "agri_data.api.app:create_app", "--factory",
             "--host", "127.0.0.1", "--port", "18080", "--no-access-log"],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        with httpx.Client(base_url="http://127.0.0.1:18080", trust_env=False, timeout=2) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Acceptance API exited; check port 18080 availability")
                try:
                    if client.get("/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Acceptance API did not become ready")
        subprocess.run([npm, "run", "test:browser"], cwd=frontend, env=env, check=True)
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        with connect(settings) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
            )
        # Restore the regular local build; acceptance credentials never enter the bundle.
        subprocess.run([npm, "run", "build"], cwd=frontend, check=True)


if __name__ == "__main__":
    main()
