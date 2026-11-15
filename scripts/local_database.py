"""Provision an isolated native development database from downloaded official binaries."""

import argparse
import json
from pathlib import Path
import secrets
import shutil
import subprocess

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
PORT = 55432


def prepare():
    pg = LOCAL / "postgresql" / "pgsql"
    bundle = LOCAL / "postgis-3.6.2" / "postgis-bundle-pg17-3.6.2x64"
    if not (pg / "bin" / "initdb.exe").is_file() or not bundle.is_dir():
        raise SystemExit("Extract the documented PostgreSQL/PostGIS archives first")
    identity = subprocess.check_output(["whoami"], text=True).strip()
    subprocess.run([
        "icacls", str(LOCAL), "/inheritance:r",
        "/grant:r", f"{identity}:(OI)(CI)F", "/Q",
    ], check=True)
    if (LOCAL / "pgdata").exists():
        raise SystemExit("Existing cluster preserved; preparation is not destructive")
    for name in ("bin", "lib", "share", "gdal-data"):
        shutil.copytree(bundle / name, pg / name, dirs_exist_ok=True)
    credentials_path = LOCAL / "database-admin.json"
    if credentials_path.exists():
        raise SystemExit("Existing credentials preserved; inspect local setup before retry")
    credentials = {"admin": secrets.token_urlsafe(32), "app": secrets.token_urlsafe(32)}
    credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
    password_path = LOCAL / "initdb-password"
    password_path.write_text(credentials["admin"], encoding="utf-8")
    try:
        subprocess.run([
            str(pg / "bin" / "initdb.exe"), "-D", str(LOCAL / "pgdata"),
            "-U", "agri_admin", "--encoding=UTF8", "--locale=C",
            "--auth-host=scram-sha-256", "--auth-local=scram-sha-256",
            f"--pwfile={password_path}",
        ], check=True)
    finally:
        password_path.unlink(missing_ok=True)


def configure():
    credentials = json.loads((LOCAL / "database-admin.json").read_text())
    options = dict(host="127.0.0.1", port=PORT, user="agri_admin",
                   password=credentials["admin"], autocommit=True, connect_timeout=5)
    with psycopg.connect(dbname="postgres", **options) as connection:
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname='agri_app'").fetchone():
            connection.execute(sql.SQL(
                "CREATE ROLE agri_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
            ).format(sql.Literal(credentials["app"])))
        if not connection.execute(
            "SELECT 1 FROM pg_database WHERE datname='agri_backend'"
        ).fetchone():
            connection.execute("CREATE DATABASE agri_backend OWNER agri_app")
    with psycopg.connect(dbname="agri_backend", **options) as connection:
        connection.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute("CREATE SCHEMA IF NOT EXISTS agri_app AUTHORIZATION agri_app")
        version = connection.execute("SELECT PostGIS_Full_Version()").fetchone()[0]
        print(version)
    env = ROOT / ".env"
    if not env.exists():
        env.write_text(
            "AGRI_ENVIRONMENT=development\n"
            f"AGRI_DATABASE_URL=postgresql+psycopg://agri_app:{credentials['app']}"
            f"@127.0.0.1:{PORT}/agri_backend\n"
            "AGRI_DATABASE_SCHEMA=agri_app\n"
            'AGRI_ALLOWED_ORIGINS=["http://localhost:1080","http://127.0.0.1:1080"]\n',
            encoding="utf-8",
        )
    print("Local PostgreSQL/PostGIS configured; credentials remain in ignored files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "configure"])
    args = parser.parse_args()
    {"prepare": prepare, "configure": configure}[args.action]()
