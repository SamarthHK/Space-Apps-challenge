import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from agri_data.api.data import DataSettings, DataStore
from agri_data.workspace.settings import WorkspaceSettings
from agri_data.workspace.store import WorkspaceStore


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
