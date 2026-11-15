import os
from dataclasses import replace
from importlib.resources import files
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from agri_data.api.data import DataSettings, DataStore
from agri_data.workspace.settings import WorkspaceSettings
from agri_data.workspace.store import WorkspaceStore
from agri_data.workspace.fields import FieldStore


@pytest.fixture
def prepared_settings():
    settings = DataSettings.from_env({
        key.replace("AGRI_TEST_", "AGRI_API_"): value
        for key, value in os.environ.items() if key.startswith("AGRI_TEST_")
    })
    assert settings and DataStore(settings).available(), "Configure real prepared PostgreSQL data"
    return settings


@pytest.fixture
def workspace_store(prepared_settings):
    schema = "agri_test_" + uuid4().hex
    settings = WorkspaceSettings(prepared_settings.dsn, prepared_settings.database,
                                 prepared_settings.user, schema, "integration")
    store = WorkspaceStore(settings)
    try:
        store.provision()
        yield store
    finally:
        with psycopg.connect(settings.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def field_store(workspace_store, prepared_settings):
    schema = workspace_store.settings.schema + "_data"
    settings = replace(prepared_settings, schema=schema, project_ids=("boundary-integration",))
    try:
        with psycopg.connect(settings.dsn) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            connection.execute(sql.SQL("SET LOCAL search_path TO {},public").format(sql.Identifier(schema)))
            for name in ("001_shared.sql", "002_context_integrity.sql", "003_boundary_imports.sql",
                         "004_boundary_job_state.sql", "005_canonical_evidence.sql"):
                connection.execute(files("agri_data").joinpath("contracts", "migrations", name).read_text("utf-8"))
            connection.execute(
                "INSERT INTO projects VALUES ('boundary-integration','Boundary integration test','{}')")
        yield FieldStore(workspace_store, settings)
    finally:
        with psycopg.connect(settings.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture
def actual_geometry(prepared_settings):
    reader = DataStore(prepared_settings)
    field = reader.fields()[0]
    return reader.get_field(field["field_id"], field["boundary_versions"][0]["boundary_id"])["geometry"]
