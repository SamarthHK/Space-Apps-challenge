"""Portable private-workspace setup; source acquisition and model execution are excluded."""

import argparse
from ipaddress import IPv4Address, IPv6Address
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

from dotenv import load_dotenv
import psycopg
import uvicorn

from agri_data.api.app import create_app
from agri_data.api.config import Settings, private_host
from agri_data.api.data import DataSettings
from agri_data.contracts.postgres import PostgresStore
from agri_data.workspace.accounts import AccountStore
from agri_data.workspace.fields import FieldStore
from agri_data.workspace.jobs import JobStore
from agri_data.workspace.errors import WorkspaceUnavailable
from agri_data.workspace.settings import AccountSettings, WorkspaceSettings
from agri_data.workspace.store import WorkspaceStore


def port(environ, name, default):
    try:
        value = int(environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be an integer port") from None
    if not 1 <= value <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return value


def public_environment(environ):
    host = environ.get("APP_HOST", "127.0.0.1")
    try:
        IPv4Address(host)
    except ValueError:
        raise ValueError("APP_HOST must be a loopback or Tailscale IPv4 address") from None
    if not private_host(host):
        raise ValueError("APP_HOST must be a loopback or Tailscale IPv4 address")
    api_port = port(environ, "API_PORT", 8080)
    frontend_port = port(environ, "FRONTEND_PORT", 1080)
    if api_port == frontend_port:
        raise ValueError("API_PORT and FRONTEND_PORT must differ")
    return {
        "AGRI_API_HOST": host, "AGRI_API_PORT": str(api_port),
        "AGRI_ALLOWED_ORIGINS": f"http://{host}:{frontend_port}",
        "FRONTEND_HOST": host, "FRONTEND_PORT": str(frontend_port),
        "VITE_API_BASE_URL": f"http://{host}:{api_port}",
    }


def deployment_environment(environ):
    values = public_environment(environ)
    host = environ.get("DB_HOST", "127.0.0.1")
    if ":" in host:
        try:
            IPv6Address(host)
        except ValueError:
            raise ValueError("Invalid DB_HOST") from None
        host = f"[{host}]"
    elif not re.fullmatch(r"[A-Za-z0-9_.-]+", host):
        raise ValueError("DB_HOST must be a database hostname or IP, not a URL")
    database = environ.get("POSTGRES_DB", "bhumi")
    user = environ.get("POSTGRES_USER", "bhumi")
    if not database or not user:
        raise ValueError("POSTGRES_DB and POSTGRES_USER cannot be empty")
    db_port = port(environ, "DB_PORT", 55432)
    password = environ.get("POSTGRES_PASSWORD") or environ.get("PGPASSWORD")
    if not password and not environ.get("PGPASSFILE"):
        raise ValueError("Set POSTGRES_PASSWORD in the ignored root .env, or configure PGPASSFILE")
    dsn = f"postgresql://{quote(user, safe='')}@{host}:{db_port}/{quote(database, safe='')}"
    values.update({
        "AGRI_AUTH_MODE": "accounts",
        "AGRI_AUTH_COOKIE_SECURE": "false",
        "AGRI_AUTH_SESSION_SECONDS": environ.get("AUTH_SESSION_SECONDS", "43200"),
        "AGRI_API_DATABASE_URL": dsn,
        "AGRI_API_DATABASE_NAME": database,
        "AGRI_API_DATABASE_USER": user,
        "AGRI_API_SCHEMA": environ.get("CANONICAL_SCHEMA", "agri_bhumi_data"),
        "AGRI_API_PROJECT_IDS": "private_deployment",
        "AGRI_WORKSPACE_DATABASE_URL": dsn,
        "AGRI_WORKSPACE_DATABASE_NAME": database,
        "AGRI_WORKSPACE_DATABASE_USER": user,
        "AGRI_WORKSPACE_SCHEMA": environ.get("WORKSPACE_SCHEMA", "agri_bhumi_workspace"),
        "AGRI_WORKSPACE_ID": environ.get("DEPLOYMENT_ID", "bhumi"),
    })
    if password:
        values["PGPASSWORD"] = password
    Settings.from_env(values)
    source = DataSettings.from_env(values)
    workspace = WorkspaceSettings.from_env(values)
    AccountSettings.from_env(values)
    if source.schema == workspace.schema:
        raise ValueError("CANONICAL_SCHEMA and WORKSPACE_SCHEMA must differ")
    return values


def stores():
    source = DataSettings.from_env()
    workspace = WorkspaceStore(WorkspaceSettings.from_env())
    accounts = AccountStore(workspace, source, AccountSettings.from_env())
    return source, workspace, accounts


def initialize():
    source, workspace, accounts = stores()
    with psycopg.connect(source.dsn, connect_timeout=5) as connection:
        if connection.execute("SELECT current_database(),current_user").fetchone() != (source.database, source.user):
            raise ValueError("Connected database/user does not match the declared identity")
        if not connection.execute("SELECT 1 FROM pg_extension WHERE extname='postgis'").fetchone():
            raise ValueError("PostGIS is not enabled; an administrator must CREATE EXTENSION postgis in this database")
        for schema, marker in ((source.schema, "schema_migrations"),
                               (workspace.settings.schema, "workspace_migrations")):
            if (connection.execute("SELECT to_regnamespace(%s)", (schema,)).fetchone()[0]
                    and not connection.execute("SELECT to_regclass(%s)", (f"{schema}.{marker}",)).fetchone()[0]):
                raise ValueError(f"Refusing to initialize existing unrecognized schema {schema}; choose a new schema name")
    PostgresStore(source.database, source.user, source.schema, connection_env="AGRI_API_DATABASE_URL").migrate()
    workspace.provision()
    if not accounts.ready():
        raise ValueError("Private storage is not ready; check migrations and database permissions")
    print("Private storage ready. Existing data is retained; no app accounts or plots were seeded.")


def check(component, container=False):
    settings = Settings.from_env()
    if component == "api":
        host = "127.0.0.1" if container else settings.bind_host
        api_port = 8080 if container else settings.port
        request = Request(f"http://{host}:{api_port}/api/v1/health",
                          headers={"Host": f"{settings.bind_host}:{settings.port}"})
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
            if json.load(response)["data"]["contract_revision"] != "private-workspace-2":
                raise ValueError("The API is not serving the private workspace contract")
    else:
        source, workspace, accounts = stores()
        if not accounts.ready():
            raise ValueError("Private account storage is not ready")
        if component == "worker" and not JobStore(
                FieldStore(workspace, source), deployment_id=workspace.settings.workspace_id).available():
            raise ValueError("No matching private worker heartbeat")
    print(f"{component} ready")


def frontend_environment(environ):
    excluded = ("AGRI_", "POSTGRES_", "PG", "DB_", "VITE_")
    clean = {key: value for key, value in environ.items()
             if not key.startswith(excluded) and key != "DATABASE_URL"}
    public = public_environment(environ)
    clean.update({key: public[key] for key in ("VITE_API_BASE_URL", "FRONTEND_HOST", "FRONTEND_PORT")})
    return clean


def frontend(directory, out_dir=None):
    directory = directory.resolve(strict=True)
    node = shutil.which("node")
    vite = directory / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.is_file():
        raise ValueError("Install Node.js 22+ and run npm --prefix frontend ci before starting the native frontend")
    environment = frontend_environment(os.environ)
    destination = [] if out_dir is None else ["--outDir", str(out_dir.resolve())]
    subprocess.run([node, str(vite), "build", *destination], cwd=directory, env=environment, check=True)
    subprocess.run([node, str(vite), "preview", "--host", environment["FRONTEND_HOST"],
                    "--port", environment["FRONTEND_PORT"], "--strictPort", *destination],
                   cwd=directory, env=environment, check=True)


def run_api(container=False):
    settings = Settings.from_env()
    app = create_app(settings, DataSettings.from_env(), WorkspaceSettings.from_env(), AccountSettings.from_env())
    # Compose publishes only the explicitly configured host; request Host/Origin checks remain unchanged.
    uvicorn.run(app, host="0.0.0.0" if container else settings.bind_host,
                port=8080 if container else settings.port, proxy_headers=False)


def main():
    parser = argparse.ArgumentParser(description="Private Bhumi deployment from the combined repository root")
    parser.add_argument("command", choices=("init", "api", "worker", "frontend", "check"))
    parser.add_argument("component", nargs="?", choices=("api", "worker", "storage"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--container", action="store_true", help="Internal API listen address; only for the supplied Compose setup")
    parser.add_argument("--frontend-dir", type=Path, default=Path("frontend"))
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    if (args.command == "check") != (args.component is not None):
        parser.error("check requires api, worker or storage; other commands do not take a component")
    if args.container and not (args.command == "api" or args.command == "check" and args.component == "api"):
        parser.error("--container is only supported for api and check api")
    load_dotenv(args.env_file, override=False, interpolate=False)
    try:
        if args.command == "frontend":
            frontend(args.frontend_dir, args.out_dir)
            return
        os.environ.update(deployment_environment(os.environ))
        if args.command == "init":
            initialize()
        elif args.command == "api":
            run_api(args.container)
        elif args.command == "worker":
            from agri_data.workspace.worker import main as worker
            worker([])
        else:
            check(args.component, args.container)
    except KeyboardInterrupt:
        parser.exit(130)
    except psycopg.Error:
        parser.exit(2, "Database setup/connection failed. Check the host, credentials, PostGIS and role permissions.\n")
    except (ValueError, OSError, WorkspaceUnavailable, subprocess.CalledProcessError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
