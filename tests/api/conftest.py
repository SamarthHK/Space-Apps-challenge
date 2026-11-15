from uuid import uuid4

import pytest
from psycopg import sql

from agri_data.api.settings import ApiSettings
from agri_data.services.database import connect, migrate


@pytest.fixture
def database_settings():
    configured = ApiSettings()
    if configured.database_url is None:
        pytest.fail("Real acceptance PostgreSQL URL is required; this is not a mock test")
    schema = "acceptance_" + uuid4().hex
    settings = configured.model_copy(update={
        "database_schema": schema, "environment": "test",
    })
    try:
        migrate(settings)
        yield settings
    finally:
        with connect(settings) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema))
            )
