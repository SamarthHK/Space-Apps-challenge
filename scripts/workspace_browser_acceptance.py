"""Run separate, owned API/frontend processes without touching existing listeners."""

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import psycopg
from psycopg import sql

from agri_data.api.data import DataSettings, DataStore
from agri_data.workspace.settings import WorkspaceSettings
from agri_data.workspace.store import WorkspaceStore


def require_free_ports(ports):
    sockets = []
    try:
        for port in ports:
            sock = socket.socket()
            sockets.append(sock)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", port))
    finally:
        for sock in sockets:
            sock.close()


def wait_ready(process, url):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("An owned acceptance service exited; inspect its run log")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.1)
    raise RuntimeError("Acceptance service did not become ready")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--api-port", type=int, default=18084)
    parser.add_argument("--frontend-port", type=int, default=11084)
    args = parser.parse_args()
    require_free_ports([args.api_port, args.frontend_port])
    prepared = DataSettings.from_env({
        key.replace("AGRI_TEST_", "AGRI_API_"): value
        for key, value in os.environ.items() if key.startswith("AGRI_TEST_")
    })
    if not prepared or not DataStore(prepared).available():
        parser.error("Set AGRI_TEST_* to the prepared authentic canonical database")
    frontend = args.frontend.resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    identifier = uuid4().hex
    artifacts = root / ".local" / "workspace-acceptance" / identifier
    artifacts.mkdir(parents=True)
    settings = WorkspaceSettings(prepared.dsn, prepared.database, prepared.user,
                                 "agri_browser_" + identifier, "browser-integration")
    api_origin = f"http://127.0.0.1:{args.api_port}"
    frontend_origin = f"http://127.0.0.1:{args.frontend_port}"
    environment = dict(os.environ, AGRI_API_HOST="127.0.0.1", AGRI_API_PORT=str(args.api_port),
        AGRI_ALLOWED_ORIGINS=frontend_origin, AGRI_API_DATABASE_URL=prepared.dsn,
        AGRI_API_DATABASE_NAME=prepared.database, AGRI_API_DATABASE_USER=prepared.user,
        AGRI_API_SCHEMA=prepared.schema, AGRI_API_PROJECT_IDS=",".join(prepared.project_ids),
        AGRI_WORKSPACE_DATABASE_URL=settings.dsn, AGRI_WORKSPACE_DATABASE_NAME=settings.database,
        AGRI_WORKSPACE_DATABASE_USER=settings.user, AGRI_WORKSPACE_SCHEMA=settings.schema,
        AGRI_WORKSPACE_ID=settings.workspace_id, VITE_API_BASE_URL=api_origin,
        TEST_API_ORIGIN=api_origin, TEST_FRONTEND_ORIGIN=frontend_origin, FRONTEND_HOST="127.0.0.1",
        PLAYWRIGHT_OUTPUT_DIR=str(artifacts / "results"))
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        parser.error("Node.js and npm are required")
    processes = []
    logs = []
    try:
        WorkspaceStore(settings).provision()
        subprocess.run([npm, "test"], cwd=frontend, env=environment, check=True)
        dist = artifacts / "dist"
        subprocess.run([node, str(frontend / "node_modules" / "vite" / "bin" / "vite.js"),
            "build", "--outDir", str(dist), "--emptyOutDir"], cwd=frontend, env=environment, check=True)
        for name, command, cwd, url in [
            ("api", [sys.executable, "-m", "agri_data.api"], root, api_origin + "/api/v1/health"),
            ("frontend", [node, str(frontend / "node_modules" / "vite" / "bin" / "vite.js"),
                "preview", "--host", "127.0.0.1", "--port", str(args.frontend_port),
                "--outDir", str(dist)], frontend, frontend_origin),
        ]:
            log = (artifacts / (name + ".log")).open("w", encoding="utf-8")
            logs.append(log)
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=log, stderr=log)
            processes.append(process)
            wait_ready(process, url)
        subprocess.run([node, str(frontend / "node_modules" / "@playwright" / "test" / "cli.js"), "test"],
                       cwd=frontend, env=environment, check=True)
        print("Separate-instance acceptance passed. Artifacts:", artifacts)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for log in logs:
            log.close()
        with psycopg.connect(settings.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(settings.schema)))


if __name__ == "__main__":
    main()
