import json
import os
import subprocess
import sys
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from agri_data.api.app import create_app
from agri_data.services.database import (
    DatabaseUnavailable, connect, migrate, verify_schema,
)


def test_real_database_migration_readiness_and_idempotency(database_settings):
    settings = database_settings
    identity = verify_schema(settings)
    assert identity["database"] == "agri_backend"
    assert identity["postgis"].startswith('POSTGIS="')
    migrate(settings)
    with connect(settings) as connection:
        assert connection.execute("SELECT count(*) AS count FROM schema_migrations").fetchone()["count"] == 1
        assert not connection.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user"
        ).fetchone()["rolsuper"]
    with TestClient(create_app(settings)) as client:
        assert client.get("/ready").status_code == 200


def test_auth_record_commit_survives_independent_process(database_settings):
    user_id = uuid4()
    with connect(database_settings) as connection:
        connection.execute(
            "INSERT INTO users (id,login,password_hash) VALUES (%s,%s,%s)",
            (user_id, "persistence-check", "not-a-login-credential"),
        )
    env = os.environ.copy()
    env["AGRI_DATABASE_URL"] = database_settings.database_url.get_secret_value()
    env["AGRI_DATABASE_SCHEMA"] = database_settings.database_schema
    script = (
        "import json; from agri_data.api.settings import ApiSettings; "
        "from agri_data.services.database import connect; "
        "c=connect(ApiSettings()); db=c.__enter__(); "
        "print(json.dumps(db.execute('SELECT id::text FROM users').fetchall())); "
        "c.__exit__(None,None,None)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == [{"id": str(user_id)}]


def test_database_constraints_rollback_entire_transaction(database_settings):
    user_id = uuid4()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with connect(database_settings) as connection:
            connection.execute(
                "INSERT INTO users (id,login,password_hash) VALUES (%s,%s,%s)",
                (user_id, "rollback-check", "not-a-login-credential"),
            )
            connection.execute(
                "INSERT INTO farmer_profiles (id,user_id) VALUES (%s,%s)",
                (uuid4(), uuid4()),
            )
    with connect(database_settings) as connection:
        assert connection.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0


def test_migration_tampering_prevents_upgrade_and_readiness(database_settings):
    with connect(database_settings) as connection:
        connection.execute("UPDATE schema_migrations SET sha256=%s", ("0" * 64,))
    with pytest.raises(DatabaseUnavailable):
        migrate(database_settings)
    with TestClient(create_app(database_settings)) as client:
        assert client.get("/ready").status_code == 503


def test_missing_schema_never_reads_another_schema(database_settings):
    missing = database_settings.model_copy(update={"database_schema": "missing_" + uuid4().hex})
    with TestClient(create_app(missing)) as client:
        assert client.get("/ready").status_code == 503
    with connect(database_settings) as connection:
        connection.execute(sql.SQL("DROP TABLE {}.profile_revisions").format(
            sql.Identifier(database_settings.database_schema)
        ))
    with TestClient(create_app(database_settings)) as client:
        assert client.get("/ready").status_code == 503
