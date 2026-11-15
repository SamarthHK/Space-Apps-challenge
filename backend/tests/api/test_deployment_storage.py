from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from agri_data import deployment


def configure(monkeypatch, prepared, canonical, workspace):
    values = {
        "AGRI_AUTH_MODE": "accounts", "AGRI_AUTH_COOKIE_SECURE": "false",
        "AGRI_API_DATABASE_URL": prepared.dsn, "AGRI_API_DATABASE_NAME": prepared.database,
        "AGRI_API_DATABASE_USER": prepared.user, "AGRI_API_SCHEMA": canonical,
        "AGRI_API_PROJECT_IDS": "private_deployment", "AGRI_WORKSPACE_DATABASE_URL": prepared.dsn,
        "AGRI_WORKSPACE_DATABASE_NAME": prepared.database, "AGRI_WORKSPACE_DATABASE_USER": prepared.user,
        "AGRI_WORKSPACE_SCHEMA": workspace, "AGRI_WORKSPACE_ID": "portable-deployment-test",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_initialization_is_repeatable_without_seeding_or_resetting_private_data(prepared_settings, monkeypatch):
    canonical, workspace = "agri_setup_" + uuid4().hex, "agri_setup_" + uuid4().hex
    configure(monkeypatch, prepared_settings, canonical, workspace)
    try:
        deployment.initialize()
        source, store, accounts = deployment.stores()
        assert accounts.ready()
        with store.session() as connection:
            assert connection.execute("SELECT count(*) AS n FROM workspace_accounts").fetchone()["n"] == 0
            assert connection.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(
                sql.Identifier(canonical, "fields"))).fetchone()["n"] == 0
            connection.execute("UPDATE workspace_profiles SET name='Retained setup diagnostic'")
        deployment.initialize()
        with store.session() as connection:
            assert connection.execute("SELECT name FROM workspace_profiles").fetchone()["name"] == "Retained setup diagnostic"
            assert connection.execute("SELECT count(*) AS n FROM workspace_profile_revisions").fetchone()["n"] == 1
    finally:
        with psycopg.connect(prepared_settings.dsn) as connection:
            for schema in (workspace, canonical):
                connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


def test_initialization_refuses_an_unrecognized_existing_schema_before_changes(prepared_settings, monkeypatch):
    canonical, workspace = "agri_setup_" + uuid4().hex, "agri_setup_" + uuid4().hex
    configure(monkeypatch, prepared_settings, canonical, workspace)
    try:
        with psycopg.connect(prepared_settings.dsn) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(canonical)))
        with pytest.raises(ValueError, match="unrecognized schema"):
            deployment.initialize()
        with psycopg.connect(prepared_settings.dsn) as connection:
            assert connection.execute("SELECT to_regnamespace(%s)", (workspace,)).fetchone()[0] is None
            assert connection.execute("SELECT to_regclass(%s)", (canonical + ".schema_migrations",)).fetchone()[0] is None
    finally:
        with psycopg.connect(prepared_settings.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(canonical)))
