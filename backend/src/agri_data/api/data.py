"""Read-only access to explicitly selected existing projects and evidence."""

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import os
import re

import psycopg
from psycopg import sql


class DataUnavailable(Exception):
    pass


class ResourceNotFound(Exception):
    pass


@dataclass(frozen=True)
class DataSettings:
    dsn: str = field(repr=False)
    database: str
    user: str
    schema: str
    project_ids: tuple[str, ...]

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        keys = ("AGRI_API_DATABASE_URL", "AGRI_API_DATABASE_NAME", "AGRI_API_DATABASE_USER",
                "AGRI_API_SCHEMA", "AGRI_API_PROJECT_IDS")
        values = [environ.get(key, "").strip() for key in keys]
        if not any(values):
            return None
        if not all(values):
            raise ValueError("All AGRI_API_DATABASE_* / SCHEMA / PROJECT_IDS settings are required together")
        dsn, database, user, schema, projects = values
        if not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("The API requires PostgreSQL; no fallback database")
        if not re.fullmatch(r"agri_[a-z0-9_]{1,58}", schema):
            raise ValueError("An explicit agri_* schema is required")
        project_ids = tuple(dict.fromkeys(item.strip() for item in projects.split(",")))
        if not all(project_ids) or "*" in project_ids:
            raise ValueError("Specify exact project IDs, never a wildcard")
        return cls(dsn, database, user, schema, project_ids)


class DataStore:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def session(self):
        if self.settings is None:
            raise DataUnavailable("Data access is not configured")
        try:
            with psycopg.connect(self.settings.dsn, connect_timeout=3) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                connection.execute("SET LOCAL statement_timeout='5s'")
                identity = connection.execute("SELECT current_database(),current_user").fetchone()
                if identity != (self.settings.database, self.settings.user):
                    raise DataUnavailable("Configured database identity does not match")
                for table in ("canonical_fields", "field_boundaries", "canonical_observations",
                              "observation_evidence", "observations"):
                    if connection.execute("SELECT to_regclass(%s)",
                                          (f"{self.settings.schema}.{table}",)).fetchone()[0] is None:
                        raise DataUnavailable("Configured project schema is not prepared")
                connection.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(
                    sql.Identifier(self.settings.schema),
                ))
                yield connection
        except psycopg.Error:
            raise DataUnavailable("Configured data store is unavailable or not prepared") from None

    def available(self):
        try:
            with self.session() as connection:
                # Checking actual columns, not just table names, detects incomplete schemas.
                connection.execute("SELECT field_id,project_id,metadata FROM canonical_fields LIMIT 0")
                connection.execute("SELECT boundary_id,field_id,geometry,metric_crs FROM field_boundaries LIMIT 0")
                connection.execute("SELECT canonical_observation_id,scientific_record FROM canonical_observations LIMIT 0")
                connection.execute("SELECT canonical_observation_id,observation_id FROM observation_evidence LIMIT 0")
            return True
        except DataUnavailable:
            return False

    def fields(self):
        with self.session() as connection:
            rows = connection.execute(
                "SELECT field_id,project_id,metadata FROM canonical_fields "
                "WHERE project_id=ANY(%s) AND metadata->>'archived' IS DISTINCT FROM 'true' ORDER BY field_id",
                (list(self.settings.project_ids),),
            ).fetchall()
            return [self._field(connection, row, None) for row in rows]

    def get_field(self, field_id, boundary_id=None):
        return self.get_field_versioned(field_id, boundary_id)[0]

    def get_field_versioned(self, field_id, boundary_id=None):
        with self.session() as connection:
            row = self._require_field(connection, field_id)
            return self._field(connection, row, boundary_id), row[2].get("workspace_version", 1)

    def _require_field(self, connection, field_id):
        row = connection.execute(
            "SELECT field_id,project_id,metadata FROM canonical_fields WHERE field_id=%s AND project_id=ANY(%s) "
            "AND metadata->>'archived' IS DISTINCT FROM 'true'",
            (field_id, list(self.settings.project_ids)),
        ).fetchone()
        if row is None:
            raise ResourceNotFound()
        return row

    def _field(self, connection, row, boundary_id):
        identifier, project_id, metadata = row
        boundaries = connection.execute(
            "SELECT boundary_id,ST_AsGeoJSON(geometry,15),source_asset_id,metric_crs,"
            "CASE WHEN metric_crs ~ '^EPSG:[0-9]+$' THEN "
            "ST_Area(ST_Transform(geometry,split_part(metric_crs,':',2)::integer)) END,"
            "CASE WHEN metric_crs ~ '^EPSG:[0-9]+$' THEN "
            "ST_Perimeter(ST_Transform(geometry,split_part(metric_crs,':',2)::integer)) END,"
            "ST_AsGeoJSON(ST_PointOnSurface(geometry),15),repair_notes "
            "FROM field_boundaries WHERE field_id=%s ORDER BY boundary_id", (identifier,),
        ).fetchall()
        chosen = next((item for item in boundaries if item[0] == boundary_id), None)
        if boundary_id and chosen is None:
            raise ResourceNotFound()
        current = next((item for item in boundaries if item[0] == metadata.get("current_boundary_id")), None)
        if current is None and len(boundaries) == 1:
            current = boundaries[0]
        if not boundary_id:
            chosen = current
        return {
            "field_id": identifier, "project_id": project_id,
            "name": metadata.get("name") if isinstance(metadata.get("name"), str) else None,
            "current_boundary_id": current[0] if current else None,
            "selected_boundary_id": chosen[0] if chosen else None,
            "geometry_status": "available" if chosen else "selection_required" if boundaries else "unavailable",
            "boundary_versions": [{"boundary_id": item[0], "source_asset_id": item[2]} for item in boundaries],
            "geometry": json.loads(chosen[1]) if chosen else None,
            "metric_crs": chosen[3] if chosen else None,
            "area_m2": chosen[4] if chosen else None,
            "area_ha": chosen[4] / 10000 if chosen and chosen[4] is not None else None,
            "perimeter_m": chosen[5] if chosen else None,
            "representative_point": json.loads(chosen[6]) if chosen else None,
            "repair_notes": chosen[7] if chosen else None,
        }

    def observations(self, field_id, variable_id=None, validation_status="all", start_date=None, end_date=None):
        with self.session() as connection:
            self._require_field(connection, field_id)
            rows = connection.execute(
                "SELECT c.canonical_observation_id,c.context_id,c.field_id,c.variable_id,c.validation_status,"
                "c.scientific_record,c.validation_evidence,"
                "(SELECT count(*) FROM observation_evidence e WHERE e.canonical_observation_id=c.canonical_observation_id),"
                "(SELECT count(*)>1 FROM canonical_observations r WHERE r.context_id=c.context_id AND r.field_id=c.field_id) "
                "FROM canonical_observations c WHERE c.field_id=%s "
                "AND (%s::text IS NULL OR c.variable_id=%s) "
                "AND (%s='all' OR c.validation_status=%s) "
                "AND (%s::date IS NULL OR (c.scientific_record->>'observed_at')::date >= %s) "
                "AND (%s::date IS NULL OR (c.scientific_record->>'observed_at')::date <= %s) "
                "ORDER BY c.canonical_observation_id",
                (field_id, variable_id, variable_id, validation_status, validation_status,
                 start_date, start_date, end_date, end_date),
            ).fetchall()
            keys = ("canonical_observation_id", "context_id", "field_id", "variable_id", "validation_status",
                    "scientific_record", "validation_evidence", "evidence_count", "has_conflicting_revisions")
            return [dict(zip(keys, row)) for row in rows]

    def observation(self, field_id, observation_id):
        result = next((row for row in self.observations(field_id)
                       if row["canonical_observation_id"] == observation_id), None)
        if result is None:
            raise ResourceNotFound()
        return result

    def evidence(self, field_id, observation_id):
        with self.session() as connection:
            self._require_field(connection, field_id)
            exists = connection.execute(
                "SELECT 1 FROM canonical_observations WHERE field_id=%s AND canonical_observation_id=%s",
                (field_id, observation_id),
            ).fetchone()
            if not exists:
                raise ResourceNotFound()
            return [row[0] for row in connection.execute(
                "SELECT o.record FROM observation_evidence e JOIN observations o USING(observation_id) "
                "WHERE e.canonical_observation_id=%s ORDER BY o.observation_id", (observation_id,),
            ).fetchall()]
