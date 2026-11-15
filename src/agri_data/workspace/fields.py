from hashlib import sha256
import json
import re
from uuid import uuid4

from psycopg import Error, sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb

from agri_data.api.data import DataStore
from agri_data.contracts.identity import fingerprint
from .errors import WorkspaceError, WorkspaceUnavailable
from .geometry import prepare_geometry


def field_etag(identifier, version):
    return f'"field:{sha256(identifier.encode()).hexdigest()[:32]}:{version}"'


def require_etag(etag):
    if etag is None:
        raise WorkspaceError(428, "precondition_required", "Read the field and supply If-Match")
    if not re.fullmatch(r'"field:[a-f0-9]{32}:[1-9][0-9]{0,18}"', etag):
        raise WorkspaceError(400, "invalid_precondition", "Supply the single strong field ETag")


def require_idempotency(key):
    if key is None:
        raise WorkspaceError(428, "idempotency_required", "Supply an Idempotency-Key for this submission")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
        raise WorkspaceError(400, "invalid_idempotency_key", "Use a 1-128 character submission identifier")


class FieldStore:
    def __init__(self, workspace, data_settings):
        self.workspace = workspace
        self.settings = data_settings

    def configured(self):
        if not self.settings or not self.workspace.settings:
            return False
        try:
            source = conninfo_to_dict(self.settings.dsn)
            target = conninfo_to_dict(self.workspace.settings.dsn)
        except Error:
            return False
        return (self.settings.database == self.workspace.settings.database and
                all(source.get(key) == target.get(key) for key in ("host", "port", "dbname")) and
                self.settings.schema != self.workspace.settings.schema)

    def table(self, name):
        if not self.configured():
            raise WorkspaceUnavailable("Field writes require separate schemas in the same configured PostgreSQL database")
        return sql.Identifier(self.settings.schema, name)

    def ready(self):
        if not self.configured() or not self.workspace.ready() or not DataStore(self.settings).available():
            return False
        try:
            with self.workspace.session() as connection:
                connection.execute("SELECT sha256,original_bytes FROM workspace_assets LIMIT 0")
                connection.execute("SELECT field_id,version,snapshot FROM workspace_field_revisions LIMIT 0")
                connection.execute("SELECT boundary_id,geometry FROM workspace_boundary_originals LIMIT 0")
                connection.execute("SELECT key,request_hash,result FROM workspace_idempotency LIMIT 0")
                for table, permissions in (("fields", ("SELECT", "INSERT", "UPDATE")),
                                           ("field_boundaries", ("SELECT", "INSERT")),
                                           ("source_assets", ("SELECT", "INSERT"))):
                    for permission in permissions:
                        if not connection.execute(
                            "SELECT has_table_privilege(current_user,%s,%s) AS allowed",
                            (self.settings.schema + "." + table, permission),
                        ).fetchone()["allowed"]:
                            return False
            return True
        except WorkspaceUnavailable:
            return False

    def require_project(self, connection, project_id):
        if not self.configured():
            raise WorkspaceUnavailable("Field writes are not configured")
        if project_id not in self.settings.project_ids or not connection.execute(
            sql.SQL("SELECT 1 FROM {} WHERE project_id=%s").format(self.table("projects")),
            (project_id,),
        ).fetchone():
            raise WorkspaceError(404, "not_found", "Project not found in this workspace")

    def idempotent(self, connection, key, operation, payload, action):
        require_idempotency(key)
        workspace_id = self.workspace.settings.workspace_id
        connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                           (workspace_id + ":submission:" + key,))
        digest = fingerprint(payload)
        previous = connection.execute(
            "SELECT operation,request_hash,result FROM workspace_idempotency WHERE workspace_id=%s AND key=%s",
            (workspace_id, key),
        ).fetchone()
        if previous:
            if (previous["operation"], previous["request_hash"]) != (operation, digest):
                raise WorkspaceError(409, "idempotency_conflict", "This submission key was used for different input")
            return previous["result"]
        result = action()
        connection.execute(
            "INSERT INTO workspace_idempotency(workspace_id,key,operation,request_hash,result) VALUES (%s,%s,%s,%s,%s)",
            (workspace_id, key, operation, digest, Jsonb(result)),
        )
        return result

    def save_asset(self, connection, filename, content, media_type, provenance):
        digest = sha256(content).hexdigest()
        settings = self.workspace.settings
        source_id = sha256(f"{settings.schema}:{settings.workspace_id}:{digest}".encode()).hexdigest()
        connection.execute(
            "INSERT INTO workspace_assets(workspace_id,sha256,filename,media_type,original_bytes) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (settings.workspace_id, digest, filename, media_type, content),
        )
        connection.execute(sql.SQL(
            "INSERT INTO {}(source_asset_id,raw_sha256,path,origin,retrieved_at,metadata) "
            "VALUES (%s,%s,%s,%s,clock_timestamp(),%s) ON CONFLICT DO NOTHING"
        ).format(self.table("source_assets")), (
            source_id, digest, f"workspace-asset://{settings.schema}/{settings.workspace_id}/{digest}",
            "shared-workspace:user-supplied", Jsonb({"filename": filename, "media_type": media_type,
                                                   "provenance": provenance}),
        ))
        return source_id

    def add_boundary(self, connection, identifier, source_id, prepared):
        boundary_id = "boundary_" + fingerprint([identifier, source_id, prepared["geometry"]])
        connection.execute(sql.SQL(
            "INSERT INTO {}(boundary_id,field_id,source_asset_id,geometry,original,repair_notes,"
            "metric_crs,area_m2,perimeter_m) "
            "SELECT %s,%s,%s,g,true,NULL,%s,ST_Area(ST_Transform(g,%s)),ST_Perimeter(ST_Transform(g,%s)) "
            "FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s),4326) AS g) geometry "
            "ON CONFLICT DO NOTHING"
        ).format(self.table("field_boundaries")), (
            boundary_id, identifier, source_id, prepared["metric_crs"],
            int(prepared["metric_crs"].split(":")[1]), int(prepared["metric_crs"].split(":")[1]),
            json.dumps(prepared["geometry"]),
        ))
        connection.execute(
            "INSERT INTO workspace_boundary_originals(workspace_id,boundary_id,geometry,properties) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (self.workspace.settings.workspace_id, boundary_id, Jsonb(prepared["original_geometry"]),
             Jsonb(prepared.get("properties", {}))),
        )
        return boundary_id

    def revision(self, connection, identifier, metadata, request_id):
        connection.execute(
            "INSERT INTO workspace_field_revisions(workspace_id,field_id,version,snapshot,request_id) "
            "VALUES (%s,%s,%s,%s,%s)",
            (self.workspace.settings.workspace_id, identifier, metadata["workspace_version"], Jsonb(metadata), request_id),
        )

    def result(self, identifier, metadata):
        return {"field_id": identifier, "version": metadata["workspace_version"],
                "current_boundary_id": metadata.get("current_boundary_id"), "archived": metadata.get("archived", False)}

    def create(self, body, key, request_id):
        payload = body.model_dump(mode="json")
        prepared = prepare_geometry(payload["geometry"])
        with self.workspace.session() as connection:
            self.require_project(connection, body.project_id)
            def insert():
                identifier = "field_" + uuid4().hex
                metadata = {"name": body.name, "workspace_version": 1, "archived": False,
                            "geometry_provenance": "user_drawn; not surveyed or scientifically verified"}
                connection.execute(sql.SQL(
                    "INSERT INTO {}(field_id,project_id,source_identifier,metadata) VALUES (%s,%s,%s,%s)"
                ).format(self.table("fields")), (identifier, body.project_id,
                    "workspace:" + self.workspace.settings.workspace_id + ":" + identifier, Jsonb(metadata)))
                content = json.dumps({"type": "Feature", "geometry": payload["geometry"],
                    "properties": {"name": body.name}}, sort_keys=True, allow_nan=False).encode()
                source_id = self.save_asset(connection, "drawn.geojson", content, "application/geo+json", "user_drawn")
                metadata["current_boundary_id"] = self.add_boundary(connection, identifier, source_id, prepared)
                self.write_metadata(connection, identifier, metadata)
                self.revision(connection, identifier, metadata, request_id)
                return self.result(identifier, metadata)
            return self.idempotent(connection, key, "createField", payload, insert)

    def locked(self, connection, identifier):
        row = connection.execute(sql.SQL(
            "SELECT f.field_id,f.project_id,f.metadata FROM {} f JOIN {} c USING(field_id) "
            "WHERE f.field_id=%s AND f.project_id=ANY(%s) FOR UPDATE OF f"
        ).format(self.table("fields"), self.table("canonical_fields")),
            (identifier, list(self.settings.project_ids))).fetchone()
        if row is None or row["metadata"].get("archived") is True:
            raise WorkspaceError(404, "not_found", "Field not found")
        return row

    def write_metadata(self, connection, identifier, metadata):
        connection.execute(sql.SQL("UPDATE {} SET metadata=%s WHERE field_id=%s").format(self.table("fields")),
                           (Jsonb(metadata), identifier))

    def update(self, identifier, body, etag, request_id, *, archive=False):
        require_etag(etag)
        changes = body.model_dump(mode="json", exclude_unset=True) if body else {}
        prepared = prepare_geometry(changes["geometry"]) if "geometry" in changes else None
        with self.workspace.session() as connection:
            row = self.locked(connection, identifier)
            metadata = row["metadata"]
            version = metadata.get("workspace_version", 1)
            if field_etag(identifier, version) != etag:
                raise WorkspaceError(412, "version_conflict", "The field changed; reload before editing")
            if "name" in changes:
                metadata["name"] = changes["name"]
            if prepared:
                content = json.dumps({"type": "Feature", "geometry": changes["geometry"],
                    "properties": {"name": metadata.get("name")}}, sort_keys=True, allow_nan=False).encode()
                source_id = self.save_asset(connection, "edited.geojson", content, "application/geo+json", "user_edited")
                metadata["current_boundary_id"] = self.add_boundary(connection, identifier, source_id, prepared)
                metadata["geometry_provenance"] = "user_edited; not surveyed or scientifically verified"
            metadata.update(workspace_version=version + 1, archived=archive)
            self.write_metadata(connection, identifier, metadata)
            self.revision(connection, identifier, metadata, request_id)
            return self.result(identifier, metadata)
