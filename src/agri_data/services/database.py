"""Real PostgreSQL connections and transactional, checksummed schema upgrades."""

from contextlib import contextmanager
import hashlib
from importlib.resources import files

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url


class DatabaseUnavailable(Exception):
    pass


def migration_files():
    return sorted(
        (item for item in files("agri_data.migrations").iterdir() if item.name.endswith(".sql")),
        key=lambda item: item.name,
    )


@contextmanager
def connect(settings):
    if settings.database_url is None:
        raise DatabaseUnavailable("PostgreSQL is not configured")
    url = make_url(settings.database_url.get_secret_value())
    options = dict(url.query)
    options.update(
        host=url.host, port=url.port or 5432, dbname=url.database,
        user=url.username, password=url.password, connect_timeout=5,
        row_factory=dict_row,
    )
    try:
        connection = psycopg.connect(**options)
    except psycopg.Error:
        raise DatabaseUnavailable("PostgreSQL connection unavailable") from None
    with connection:
        connection.execute(
            sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(
                sql.Identifier(settings.database_schema)
            )
        )
        connection.execute("SET LOCAL statement_timeout = '10s'")
        yield connection


def migrate(settings):
    with connect(settings) as connection:
        connection.execute("SELECT public.PostGIS_Full_Version()")
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (f"agri-migrations:{settings.database_schema}",),
        )
        connection.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(settings.database_schema)
            )
        )
        connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name text PRIMARY KEY,
                sha256 varchar(64) NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
            )
        """)
        recorded = {
            row["name"]: row["sha256"]
            for row in connection.execute("SELECT name, sha256 FROM schema_migrations")
        }
        known = {item.name for item in migration_files()}
        if recorded.keys() - known:
            raise DatabaseUnavailable("Database schema is newer than this application")
        for item in migration_files():
            content = item.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            if item.name in recorded:
                if recorded[item.name] != checksum:
                    raise DatabaseUnavailable("Applied migration checksum differs")
                continue
            connection.execute(content.decode("utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (name, sha256) VALUES (%s, %s)",
                (item.name, checksum),
            )


def verify_schema(settings):
    with connect(settings) as connection:
        identity = connection.execute(
            "SELECT current_database() AS database, current_user AS role, "
            "public.PostGIS_Full_Version() AS postgis"
        ).fetchone()
        recorded = {
            row["name"]: row["sha256"]
            for row in connection.execute(
                sql.SQL("SELECT name, sha256 FROM {}.schema_migrations").format(
                    sql.Identifier(settings.database_schema)
                )
            )
        }
        expected = {
            item.name: hashlib.sha256(item.read_bytes()).hexdigest()
            for item in migration_files()
        }
        if recorded != expected:
            raise DatabaseUnavailable("Required migrations do not match")
        for table in ("users", "farmer_profiles", "profile_revisions", "auth_sessions", "login_attempts"):
            connection.execute(
                sql.SQL("SELECT 1 FROM {}.{} LIMIT 0").format(
                    sql.Identifier(settings.database_schema), sql.Identifier(table)
                )
            )
        return identity


if __name__ == "__main__":
    from agri_data.api.settings import ApiSettings

    settings = ApiSettings()
    migrate(settings)
    verify_schema(settings)
    print("PostgreSQL/PostGIS migrations applied and verified.")
