"""Real PostgreSQL/PostGIS persistence; no default server or alternative database."""

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import json
import os
import re

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from .observation import Observation
from .canonical import AUDIT_FIELDS


class PostgresStore:
    def __init__(self, database: str, user: str, schema: str, connection_env="DATABASE_URL"):
        if not database or not user or not re.fullmatch(r"agri_[a-z0-9_]+", schema):
            raise ValueError("Expected database/user and an explicitly acceptance-owned agri_* schema are required")
        self.database, self.user, self.schema = database, user, schema
        self.connection_env = connection_env
        self.dsn = os.environ.get(connection_env)
        if not self.dsn or not self.dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("Configure a PostgreSQL connection environment variable; no database fallback is allowed")

    @contextmanager
    def session(self, *, repeatable_read=False):
        with psycopg.connect(self.dsn, connect_timeout=10) as connection:
            if repeatable_read:
                connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            identity = connection.execute(
                "SELECT current_database(), current_user, version(), PostGIS_Full_Version()"
            ).fetchone()
            if identity[0] != self.database or identity[1] != self.user:
                raise ValueError("Connected database/user does not match the declared acceptance identity")
            connection.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(self.schema)))
            yield connection

    def migrate(self):
        with self.session() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self.schema,))
            connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(self.schema)))
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                payload = path.read_bytes()
                checksum = sha256(payload).hexdigest()
                previous = connection.execute(
                    "SELECT sha256 FROM schema_migrations WHERE version=%s", (path.name,)
                ).fetchone()
                if previous:
                    if previous[0] != checksum:
                        raise ValueError("An applied migration was modified; add a new version instead")
                    continue
                connection.execute(payload.decode("utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version,sha256) VALUES (%s,%s)", (path.name, checksum)
                )

    def identity(self):
        with self.session() as connection:
            result = connection.execute(
                "SELECT current_database(),current_user,version(),PostGIS_Full_Version()"
            ).fetchone()
            return dict(zip(("database", "user", "postgresql", "postgis"), result))

    def save_observation(self, connection, observation: Observation):
        record = observation.model_dump(mode="json")
        previous = connection.execute(
            "SELECT record FROM observations WHERE observation_id=%s", (observation.observation_id,)
        ).fetchone()
        if previous:
            if ({k: v for k, v in previous[0].items() if k not in AUDIT_FIELDS}
                    != {k: v for k, v in record.items() if k not in AUDIT_FIELDS}):
                raise ValueError("Observation ID conflict: changed evidence requires a distinct version/context ID")
            self._save_receipt(connection, record)
            return False
        scalar_fields = (
            "observation_id", "schema_version", "variable_id", "feature_id", "subject_id",
            "field_id", "source_id", "dataset_id", "source_binding_id", "source_asset_id",
            "extraction_job_id", "value_numeric", "value_text", "value_boolean", "value_date",
            "value_series_ref", "observed_at", "period_start", "period_end", "retrieved_at",
            "depth_top_cm", "depth_bottom_cm", "standardized_unit", "evidence_type", "validation_status",
        )
        names = list(scalar_fields) + ["observed_timezone", "value_geometry", "record"]
        values = [record[key] for key in scalar_fields] + [
            record["timezone"],
            json.dumps(record["value_geometry"]) if record["value_geometry"] is not None else None,
            Jsonb(record),
        ]
        placeholders = [sql.Placeholder() for _ in scalar_fields] + [
            sql.Placeholder(), sql.SQL("ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)"), sql.Placeholder(),
        ]
        connection.execute(sql.SQL("INSERT INTO observations ({}) VALUES ({})").format(
            sql.SQL(",").join(map(sql.Identifier, names)), sql.SQL(",").join(placeholders)
        ), values)
        for parent in observation.parent_observation_ids:
            connection.execute(
                "INSERT INTO observation_lineage VALUES (%s,%s)", (observation.observation_id, parent)
            )
        self._save_receipt(connection, record)
        return True

    def _save_receipt(self, connection, record):
        previous = connection.execute(
            "SELECT acquired_record FROM acquisition_observations "
            "WHERE extraction_job_id=%s AND observation_id=%s",
            (record["extraction_job_id"], record["observation_id"]),
        ).fetchone()
        if previous and previous[0] != record:
            raise ValueError("An acquisition receipt cannot be changed in place")
        connection.execute(
            "INSERT INTO acquisition_observations VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (record["extraction_job_id"], record["observation_id"], Jsonb(record)),
        )

    def read_observations(self, job_id):
        with self.session() as connection:
            records = connection.execute(
                "SELECT acquired_record FROM acquisition_observations "
                "WHERE extraction_job_id=%s ORDER BY observation_id", (job_id,)
            ).fetchall()
            return [Observation.model_validate(row[0]) for row in records]
