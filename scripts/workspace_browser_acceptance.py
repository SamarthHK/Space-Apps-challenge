"""Run separate, owned API/frontend processes without touching existing listeners."""

import argparse
from dataclasses import replace
import json
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
from agri_data.workspace.fields import FieldStore
from agri_data.workspace.jobs import JobStore
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


def wait_ready(process, url, capability=None, predicate=None):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("An owned acceptance service exited; inspect its run log")
        if predicate is not None:
            if predicate():
                return
            time.sleep(0.1)
            continue
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200 and (capability is None or any(
                    item["capability_id"] == capability and item["state"] == "ready"
                    for item in json.load(response)["data"]["capabilities"]
                )):
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.1)
    raise RuntimeError("Acceptance service did not become ready")


def copy_scoped_reference(prepared, schema):
    source = lambda table: sql.Identifier(prepared.schema, table)
    target = lambda table: sql.Identifier(schema, table)
    with psycopg.connect(prepared.dsn) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for name in ("projects", "fields", "source_assets", "field_boundaries", "observations",
                     "field_aliases", "canonical_observations", "observation_evidence"):
            connection.execute(sql.SQL("CREATE TABLE {} (LIKE {} INCLUDING ALL)").format(target(name), source(name)))
        connection.execute(sql.SQL("INSERT INTO {} SELECT * FROM {} WHERE project_id=ANY(%s)").format(
            target("projects"), source("projects")), (list(prepared.project_ids),))
        connection.execute(sql.SQL("INSERT INTO {} SELECT * FROM {} WHERE project_id=ANY(%s)").format(
            target("fields"), source("fields")), (list(prepared.project_ids),))
        for name in ("field_boundaries", "observations", "canonical_observations"):
            connection.execute(sql.SQL(
                "INSERT INTO {} SELECT r.* FROM {} r JOIN {} f ON r.field_id=f.field_id"
            ).format(target(name), source(name), target("fields")))
        connection.execute(sql.SQL(
            "INSERT INTO {} SELECT a.* FROM {} a JOIN {} f ON a.alias_field_id=f.field_id "
            "JOIN {} c ON a.canonical_field_id=c.field_id"
        ).format(target("field_aliases"), source("field_aliases"), target("fields"), target("fields")))
        connection.execute(sql.SQL(
            "INSERT INTO {} SELECT e.* FROM {} e JOIN {} c USING(canonical_observation_id) "
            "JOIN {} o USING(observation_id)"
        ).format(target("observation_evidence"), source("observation_evidence"),
                 target("canonical_observations"), target("observations")))
        connection.execute(sql.SQL(
            "INSERT INTO {} SELECT * FROM {} WHERE source_asset_id IN "
            "(SELECT source_asset_id FROM {} UNION SELECT source_asset_id FROM {})"
        ).format(target("source_assets"), source("source_assets"), target("field_boundaries"), target("observations")))
        connection.execute(sql.SQL(
            "CREATE VIEW {} AS SELECT f.* FROM {} f WHERE NOT EXISTS "
            "(SELECT 1 FROM {} a WHERE a.alias_field_id=f.field_id)"
        ).format(target("canonical_fields"), target("fields"), target("field_aliases")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--api-port", type=int, default=18084)
    parser.add_argument("--frontend-port", type=int, default=11084)
    parser.add_argument("--mode", choices=("shared", "accounts", "both"), default="shared")
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
    source = replace(prepared, schema=settings.schema + "_data")
    api_origin = f"http://127.0.0.1:{args.api_port}"
    frontend_origin = f"http://127.0.0.1:{args.frontend_port}"
    environment = dict(os.environ, AGRI_API_HOST="127.0.0.1", AGRI_API_PORT=str(args.api_port),
        AGRI_ALLOWED_ORIGINS=frontend_origin, AGRI_API_DATABASE_URL=prepared.dsn,
        AGRI_API_DATABASE_NAME=prepared.database, AGRI_API_DATABASE_USER=prepared.user,
        AGRI_API_SCHEMA=source.schema, AGRI_API_PROJECT_IDS=",".join(prepared.project_ids),
        AGRI_WORKSPACE_DATABASE_URL=settings.dsn, AGRI_WORKSPACE_DATABASE_NAME=settings.database,
        AGRI_WORKSPACE_DATABASE_USER=settings.user, AGRI_WORKSPACE_SCHEMA=settings.schema,
        AGRI_WORKSPACE_ID=settings.workspace_id, VITE_API_BASE_URL=api_origin,
        TEST_API_ORIGIN=api_origin, TEST_FRONTEND_ORIGIN=frontend_origin, FRONTEND_HOST="127.0.0.1",
        TEST_WRITES_ISOLATED="1", AGRI_AUTH_COOKIE_SECURE="false", AGRI_AUTH_SESSION_SECONDS="43200")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        parser.error("Node.js and npm are required")
    processes = []
    logs = []
    def stop(owned):
        for process in reversed(owned):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def launch(name, command, cwd, env, url, **readiness):
        log = (artifacts / (name + ".log")).open("w", encoding="utf-8")
        logs.append(log)
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log)
        processes.append(process)
        wait_ready(process, url, **readiness)
        return process

    try:
        copy_scoped_reference(prepared, source.schema)
        WorkspaceStore(settings).provision()
        subprocess.run([npm, "test"], cwd=frontend, env=environment, check=True)
        dist = artifacts / "dist"
        subprocess.run([node, str(frontend / "node_modules" / "vite" / "bin" / "vite.js"),
            "build", "--outDir", str(dist), "--emptyOutDir"], cwd=frontend, env=environment, check=True)
        launch("frontend", [node, str(frontend / "node_modules" / "vite" / "bin" / "vite.js"),
            "preview", "--host", "127.0.0.1", "--port", str(args.frontend_port), "--outDir", str(dist)],
            frontend, environment, frontend_origin)
        modes = ("shared", "accounts") if args.mode == "both" else (args.mode,)
        for mode in modes:
            env = dict(environment, AGRI_AUTH_MODE=mode, TEST_AUTH_MODE=mode,
                       PLAYWRIGHT_OUTPUT_DIR=str(artifacts / ("results-" + mode)))
            owned = []
            try:
                owned.append(launch("api-" + mode, [sys.executable, "-m", "agri_data.api"],
                                    root, env, api_origin + "/api/v1/health"))
                readiness = ({"predicate": JobStore(FieldStore(WorkspaceStore(settings), source),
                              deployment_id=settings.workspace_id).available} if mode == "accounts"
                             else {"capability": "imports"})
                owned.append(launch("worker-" + mode, [sys.executable, "-m", "agri_data.workspace.worker"],
                                    root, env, api_origin + "/api/v1/workspace", **readiness))
                subprocess.run([node, str(frontend / "node_modules" / "@playwright" / "test" / "cli.js"), "test"],
                               cwd=frontend, env=env, check=True)
            finally:
                stop(owned)
        print("Separate-instance acceptance passed. Artifacts:", artifacts)
    finally:
        stop(processes)
        for log in logs:
            log.close()
        with psycopg.connect(settings.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                sql.Identifier(settings.schema)))
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(source.schema)))


if __name__ == "__main__":
    main()
