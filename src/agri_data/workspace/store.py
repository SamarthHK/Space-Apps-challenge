from contextlib import contextmanager
from hashlib import sha256
from importlib.resources import files
import re

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .errors import WorkspaceError, WorkspaceUnavailable


def migration_files():
    return sorted((entry for entry in files("agri_data.workspace").joinpath("migrations").iterdir()
                   if entry.name.endswith(".sql")), key=lambda entry: entry.name)


def profile_etag(profile):
    return f'"profile:{profile["workspace_id"]}:{profile["version"]}"'


class WorkspaceStore:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def session(self):
        if self.settings is None:
            raise WorkspaceUnavailable("Shared workspace storage is not configured")
        try:
            with psycopg.connect(self.settings.dsn, connect_timeout=3, row_factory=dict_row) as connection:
                identity = connection.execute(
                    "SELECT current_database() AS database,current_user AS role"
                ).fetchone()
                if (identity["database"], identity["role"]) != (self.settings.database, self.settings.user):
                    raise WorkspaceUnavailable("Workspace database identity does not match")
                connection.execute(sql.SQL("SET LOCAL search_path TO {},public").format(
                    sql.Identifier(self.settings.schema)))
                connection.execute("SET LOCAL statement_timeout='10s'")
                yield connection
        except psycopg.Error:
            raise WorkspaceUnavailable("Workspace database or schema is unavailable") from None

    def migrate(self):
        with self.session() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                               ("workspace-migrations:" + self.settings.schema,))
            connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(self.settings.schema)))
            connection.execute(
                "CREATE TABLE IF NOT EXISTS workspace_migrations "
                "(name text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT now())"
            )
            recorded = {row["name"]: row["sha256"] for row in connection.execute(
                "SELECT name,sha256 FROM workspace_migrations")}
            migrations = migration_files()
            if recorded.keys() - {entry.name for entry in migrations}:
                raise WorkspaceUnavailable("Workspace schema is newer than this application")
            for entry in migrations:
                content = entry.read_bytes()
                digest = sha256(content).hexdigest()
                if entry.name in recorded:
                    if recorded[entry.name] != digest:
                        raise WorkspaceUnavailable("Workspace migration checksum differs")
                    continue
                connection.execute(content.decode("utf-8"))
                connection.execute("INSERT INTO workspace_migrations(name,sha256) VALUES (%s,%s)",
                                   (entry.name, digest))

    def provision(self):
        self.migrate()
        with self.session() as connection:
            row = connection.execute(
                "INSERT INTO workspace_profiles(workspace_id) VALUES (%s) ON CONFLICT DO NOTHING "
                "RETURNING workspace_id", (self.settings.workspace_id,),
            ).fetchone()
            if row:
                self._revision(connection, "provision")

    def ready(self):
        try:
            with self.session() as connection:
                recorded = {row["name"]: row["sha256"] for row in connection.execute(
                    "SELECT name,sha256 FROM workspace_migrations")}
                expected = {entry.name: sha256(entry.read_bytes()).hexdigest() for entry in migration_files()}
                if recorded != expected:
                    return False
                permissions = connection.execute(
                    "SELECT has_table_privilege(current_user,%s,'SELECT') "
                    "AND has_table_privilege(current_user,%s,'UPDATE') "
                    "AND has_table_privilege(current_user,%s,'INSERT') AS allowed",
                    (self.settings.schema + ".workspace_profiles",
                     self.settings.schema + ".workspace_profiles",
                     self.settings.schema + ".workspace_profile_revisions"),
                ).fetchone()
                return permissions["allowed"] and self._profile(connection) is not None
        except WorkspaceUnavailable:
            return False

    def _profile(self, connection):
        return connection.execute("SELECT * FROM workspace_profiles WHERE workspace_id=%s",
                                  (self.settings.workspace_id,)).fetchone()

    def get_profile(self):
        with self.session() as connection:
            profile = self._profile(connection)
        if profile is None:
            raise WorkspaceUnavailable("Provision the shared workspace before using its profile")
        return profile

    def _revision(self, connection, request_id):
        connection.execute(
            "INSERT INTO workspace_profile_revisions(workspace_id,version,snapshot,request_id) "
            "SELECT workspace_id,version,to_jsonb(workspace_profiles),%s "
            "FROM workspace_profiles WHERE workspace_id=%s",
            (request_id, self.settings.workspace_id),
        )

    def update_profile(self, patch, etag, request_id):
        if etag is None:
            raise WorkspaceError(428, "precondition_required", "Read the profile and supply If-Match")
        if not re.fullmatch(r'"profile:[A-Za-z0-9_-]{1,64}:[1-9][0-9]{0,18}"', etag):
            raise WorkspaceError(400, "invalid_precondition", "Supply the single strong profile ETag")
        changes = patch.model_dump(exclude_unset=True)
        with self.session() as connection:
            current = self._profile(connection)
            if current is None:
                raise WorkspaceUnavailable("Shared profile is not provisioned")
            if profile_etag(current) != etag:
                raise WorkspaceError(412, "version_conflict", "The shared profile changed; reload before saving")
            assignments = [sql.SQL("{}=%s").format(sql.Identifier(name)) for name in changes]
            profile = connection.execute(sql.SQL(
                "UPDATE workspace_profiles SET {},version=version+1,updated_at=clock_timestamp() "
                "WHERE workspace_id=%s AND version=%s RETURNING *"
            ).format(sql.SQL(",").join(assignments)),
                (*changes.values(), self.settings.workspace_id, current["version"])).fetchone()
            if profile is None:
                raise WorkspaceError(412, "version_conflict", "The shared profile changed; reload before saving")
            self._revision(connection, request_id)
        return profile
