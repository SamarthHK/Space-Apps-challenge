from hashlib import sha256
from pathlib import Path
import re
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from agri_data.api.data import DataStore, ResourceNotFound
from agri_data.contracts.identity import fingerprint, stable_field_id
from .errors import WorkspaceError, WorkspaceUnavailable
from .formats import MEDIA_TYPES, parse_upload, serialize_export


PROTOCOL = "workspace-jobs-1"
ACCOUNT_PROTOCOL = "workspace-account-jobs-1"


class JobStore:
    def __init__(self, fields, *, deployment_id=None):
        self.fields = fields
        self.workspace = fields.workspace
        self.deployment_id = deployment_id

    @property
    def workspace_id(self):
        return self.workspace.settings.workspace_id

    @property
    def projects(self):
        if not self.fields.configured():
            raise WorkspaceUnavailable("Explicit shared job project configuration is required")
        return list(self.fields.settings.project_ids)

    def public(self, row):
        return {**{key: row[key] for key in ("job_id", "resource_id", "kind", "status", "attempts", "result", "error")},
                "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()}

    def get(self, identifier, connection=None):
        if connection is None:
            with self.workspace.session() as connection:
                return self.get(identifier, connection)
        row = connection.execute(
            "SELECT * FROM workspace_jobs WHERE job_id=%s AND workspace_id=%s AND project_ids <@ %s::text[]",
            (identifier, self.workspace_id, self.projects),
        ).fetchone()
        if row is None:
            raise WorkspaceError(404, "not_found", "Job not found")
        return self.public(row)

    def heartbeat(self, worker_id):
        with self.workspace.session() as connection:
            connection.execute(
                "INSERT INTO workspace_workers(worker_id,workspace_id,project_ids,protocol) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT(worker_id) DO UPDATE SET heartbeat_at=clock_timestamp(),project_ids=EXCLUDED.project_ids,"
                "protocol=EXCLUDED.protocol", (worker_id, self.workspace_id, self.projects, PROTOCOL),
            )

    def remove_worker(self, worker_id):
        with self.workspace.session() as connection:
            connection.execute("DELETE FROM workspace_workers WHERE worker_id=%s AND workspace_id=%s",
                               (worker_id, self.workspace_id))

    def available(self):
        try:
            with self.workspace.session() as connection:
                if self.deployment_id is not None:
                    return connection.execute(
                        "SELECT 1 FROM workspace_workers WHERE workspace_id=%s AND protocol=%s "
                        "AND canonical_schema=%s AND heartbeat_at>clock_timestamp()-interval '30 seconds' LIMIT 1",
                        (self.deployment_id, ACCOUNT_PROTOCOL, self.fields.settings.schema),
                    ).fetchone() is not None
                return connection.execute(
                    "SELECT 1 FROM workspace_workers WHERE workspace_id=%s AND protocol=%s "
                    "AND project_ids @> %s::text[] AND heartbeat_at > clock_timestamp()-interval '30 seconds' LIMIT 1",
                    (self.workspace_id, PROTOCOL, self.projects),
                ).fetchone() is not None
        except WorkspaceUnavailable:
            return False

    def enqueue(self, connection, kind, resource_id, projects, payload):
        identifier = "job_" + uuid4().hex
        row = connection.execute(
            "INSERT INTO workspace_jobs(job_id,workspace_id,resource_id,kind,project_ids,payload) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (identifier, self.workspace_id, resource_id, kind, projects, Jsonb(payload)),
        ).fetchone()
        return self.public(row)

    def submit_import(self, content, filename, project_id, namespace, key):
        if (not re.fullmatch(r"[^/\\:\x00-\x1f]{1,160}", filename)
                or Path(filename).suffix.lower()[1:] not in MEDIA_TYPES):
            raise WorkspaceError(422, "invalid_filename", "Use a plain .kml, .kmz, or .geojson filename")
        if not 0 < len(content) <= 16 * 1024 * 1024:
            raise WorkspaceError(413, "invalid_upload_size", "Upload between 1 byte and 16 MiB")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", namespace):
            raise WorkspaceError(422, "invalid_namespace", "Supply a stable 1-80 character source namespace")
        digest = sha256(content).hexdigest()
        with self.workspace.session() as connection:
            self.fields.require_project(connection, project_id)
            def insert():
                identifier = "import_" + uuid4().hex
                connection.execute(
                    "INSERT INTO workspace_assets(workspace_id,sha256,filename,media_type,original_bytes) "
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (self.workspace_id, digest, filename, MEDIA_TYPES[Path(filename).suffix.lower()[1:]], content),
                )
                job = self.enqueue(connection, "import_preview", identifier, [project_id], {})
                connection.execute(
                    "INSERT INTO workspace_imports(import_id,workspace_id,project_id,source_namespace,filename,sha256,"
                    "preview_job_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (identifier, self.workspace_id, project_id, namespace, filename, digest, job["job_id"]),
                )
                return job
            return self.fields.idempotent(connection, key, "createBoundaryImport",
                [digest, filename, project_id, namespace], insert)

    def import_row(self, connection, identifier, *, lock=False):
        row = connection.execute(
            "SELECT * FROM workspace_imports WHERE import_id=%s AND workspace_id=%s AND project_id=ANY(%s)"
            + (" FOR UPDATE" if lock else ""), (identifier, self.workspace_id, self.projects),
        ).fetchone()
        if row is None:
            raise WorkspaceError(404, "not_found", "Import not found")
        return row

    def import_info(self, identifier):
        with self.workspace.session() as connection:
            row = self.import_row(connection, identifier)
        return {**{key: row[key] for key in ("import_id", "project_id", "source_namespace", "filename", "sha256",
                                            "preview_job_id", "preview_hash", "confirmed_job_id")},
                "candidates": (row["preview"] or {}).get("candidates", []),
                "rejected": (row["preview"] or {}).get("rejected", [])}

    def confirm(self, identifier, payload, key):
        with self.workspace.session() as connection:
            row = self.import_row(connection, identifier, lock=True)
            if row["preview"] is None or payload["preview_hash"] != row["preview_hash"]:
                raise WorkspaceError(409, "preview_changed", "Load a completed preview before confirming it")
            candidates = {candidate["candidate_id"] for candidate in row["preview"]["candidates"]}
            if (not payload["candidate_ids"] or len(set(payload["candidate_ids"])) != len(payload["candidate_ids"])
                    or not set(payload["candidate_ids"]) <= candidates):
                raise WorkspaceError(422, "invalid_selection", "Select distinct valid candidates from this preview")
            def insert():
                if row["confirmed_job_id"]:
                    if row["confirmation_hash"] != fingerprint(payload):
                        raise WorkspaceError(409, "already_confirmed", "This import was confirmed with a different selection")
                    return self.get(row["confirmed_job_id"], connection)
                job = self.enqueue(connection, "import_confirm", identifier, [row["project_id"]], payload)
                connection.execute(
                    "UPDATE workspace_imports SET confirmed_job_id=%s,confirmation_hash=%s WHERE import_id=%s",
                    (job["job_id"], fingerprint(payload), identifier),
                )
                return job
            return self.fields.idempotent(connection, key, "confirmBoundaryImport", [identifier, payload], insert)

    def submit_export(self, payload, key):
        reader = DataStore(self.fields.settings)
        records = []
        with reader.session() as source:
            for selection in payload["fields"]:
                row = reader._require_field(source, selection["field_id"])
                record = reader._field(source, row, selection["boundary_id"])
                if record["geometry"] is None:
                    raise WorkspaceError(409, "boundary_selection_required", "Select an explicit stored boundary to export")
                records.append(record)
        with self.workspace.session() as connection:
            def insert():
                features = []
                for record in records:
                    original = connection.execute(
                        "SELECT geometry,properties FROM workspace_boundary_originals WHERE workspace_id=%s AND boundary_id=%s",
                        (self.workspace_id, record["selected_boundary_id"]),
                    ).fetchone()
                    features.append({"type": "Feature", "id": record["field_id"],
                        "geometry": original["geometry"] if original else record["geometry"],
                        "properties": {"field_id": record["field_id"], "project_id": record["project_id"],
                            "boundary_id": record["selected_boundary_id"], "name": record["name"],
                            "metric_crs": record["metric_crs"], "area_m2": record["area_m2"],
                            "source_metadata": original["properties"] if original else {},
                            "altitude_status": "original retained" if original else "canonical geometry; no altitude reconstructed"}})
                identifier = "export_" + uuid4().hex
                projects = sorted({record["project_id"] for record in records})
                job = self.enqueue(connection, "export", identifier, projects,
                                   {"features": features, "format": payload["format"]})
                connection.execute(
                    "INSERT INTO workspace_exports(export_id,workspace_id,job_id,project_ids,field_ids,filename,media_type) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (identifier, self.workspace_id, job["job_id"], projects, [record["field_id"] for record in records],
                     identifier + "." + payload["format"], MEDIA_TYPES[payload["format"]]),
                )
                return job
            return self.fields.idempotent(connection, key, "createExport", payload, insert)

    def download(self, identifier):
        with self.workspace.session() as connection:
            row = connection.execute(
                "SELECT * FROM workspace_exports WHERE export_id=%s AND workspace_id=%s AND project_ids <@ %s::text[]",
                (identifier, self.workspace_id, self.projects),
            ).fetchone()
            if row is None:
                raise WorkspaceError(404, "not_found", "Export not found")
            for field_id in sorted(set(row["field_ids"])):
                self.fields.locked(connection, field_id)
            if row["content"] is None:
                raise WorkspaceError(409, "export_not_ready", "The export job has not completed")
            return row

    def claim(self, worker_id):
        with self.workspace.session() as connection:
            connection.execute(
                "WITH exhausted AS (SELECT job_id FROM workspace_jobs WHERE workspace_id=%s "
                "AND project_ids <@ %s::text[] AND status='running' AND lease_until < clock_timestamp() "
                "AND attempts>=3 FOR UPDATE SKIP LOCKED) "
                "UPDATE workspace_jobs SET status='failed',lease_owner=NULL,lease_until=NULL,error=%s,"
                "updated_at=clock_timestamp() WHERE job_id IN (SELECT job_id FROM exhausted)",
                (self.workspace_id, self.projects,
                 Jsonb({"code": "attempt_limit", "message": "Worker recovery attempt limit reached", "retryable": False})),
            )
            row = connection.execute(
                "SELECT job_id FROM workspace_jobs WHERE workspace_id=%s AND project_ids <@ %s::text[] AND attempts<3 "
                "AND ((status='queued' AND available_at<=clock_timestamp()) OR "
                "(status='running' AND lease_until<clock_timestamp())) "
                "ORDER BY created_at,job_id FOR UPDATE SKIP LOCKED LIMIT 1",
                (self.workspace_id, self.projects),
            ).fetchone()
            if row is None:
                return None
            token = worker_id + ":" + uuid4().hex
            connection.execute(
                "UPDATE workspace_jobs SET status='running',attempts=attempts+1,lease_owner=%s,"
                "lease_until=clock_timestamp()+interval '60 seconds',updated_at=clock_timestamp(),error=NULL "
                "WHERE job_id=%s", (token, row["job_id"]),
            )
            return row["job_id"], token

    def run_once(self, worker_id):
        claimed = self.claim(worker_id)
        if claimed is None:
            return False
        identifier, token = claimed
        try:
            with self.workspace.session() as connection:
                job = connection.execute(
                    "SELECT * FROM workspace_jobs WHERE job_id=%s AND workspace_id=%s FOR UPDATE",
                    (identifier, self.workspace_id),
                ).fetchone()
                if job["lease_owner"] != token or job["status"] != "running":
                    return True
                result = self.perform(connection, job)
                connection.execute(
                    "UPDATE workspace_jobs SET status='succeeded',result=%s,error=NULL,lease_owner=NULL,lease_until=NULL,"
                    "updated_at=clock_timestamp() WHERE job_id=%s", (Jsonb(result), identifier),
                )
        except (WorkspaceError, WorkspaceUnavailable, ResourceNotFound) as error:
            self.fail(identifier, token, error)
        except Exception:
            self.fail(identifier, token, WorkspaceError(500, "job_failed", "Job failed without changing fields"))
        return True

    def fail(self, identifier, token, error):
        retryable = isinstance(error, WorkspaceUnavailable)
        failure = {"code": getattr(error, "code", "storage_unavailable" if retryable else "not_found"),
                   "message": str(error) or "A scoped resource is unavailable", "retryable": retryable}
        with self.workspace.session() as connection:
            connection.execute(
                "UPDATE workspace_jobs SET status=CASE WHEN %s AND attempts<3 THEN 'queued' ELSE 'failed' END,"
                "error=%s,lease_owner=NULL,lease_until=NULL,available_at=clock_timestamp()+interval '2 seconds',"
                "updated_at=clock_timestamp() WHERE job_id=%s AND lease_owner=%s AND status='running'",
                (retryable, Jsonb(failure), identifier, token),
            )

    def perform(self, connection, job):
        if job["kind"] == "export":
            exported = connection.execute("SELECT field_ids FROM workspace_exports WHERE export_id=%s",
                                          (job["resource_id"],)).fetchone()
            for field_id in sorted(set(exported["field_ids"])):
                self.fields.locked(connection, field_id)
            content = serialize_export(job["payload"]["features"], job["payload"]["format"])
            if len(content) > 32 * 1024 * 1024:
                raise WorkspaceError(413, "export_too_large", "Export exceeds 32 MiB; select fewer fields")
            digest = sha256(content).hexdigest()
            connection.execute("UPDATE workspace_exports SET content=%s,sha256=%s WHERE export_id=%s",
                               (content, digest, job["resource_id"]))
            return {"export_id": job["resource_id"], "sha256": digest, "bytes": len(content)}
        row = self.import_row(connection, job["resource_id"], lock=True)
        asset = connection.execute(
            "SELECT original_bytes FROM workspace_assets WHERE workspace_id=%s AND sha256=%s",
            (self.workspace_id, row["sha256"]),
        ).fetchone()
        content = bytes(asset["original_bytes"])
        if sha256(content).hexdigest() != row["sha256"]:
            raise WorkspaceError(409, "asset_changed", "Original upload checksum differs")
        if job["kind"] == "import_preview":
            return self.preview(connection, row, content)
        return self.apply_import(connection, job, row, content)

    def preview(self, connection, row, content):
        namespace = "workspace:" + self.workspace_id + ":" + row["source_namespace"]
        candidates, rejected = parse_upload(content, row["filename"], row["project_id"], namespace)
        accepted = []
        for candidate in candidates:
            if (candidate["name"] is not None and
                (not isinstance(candidate["name"], str) or len(candidate["name"]) > 200)):
                rejected.append({"locator": candidate["locator"], "reason": "Field name exceeds 200 characters or is not text"})
                continue
            identifier = stable_field_id(row["project_id"], namespace, candidate["source_identifier"])
            existing = connection.execute(sql.SQL(
                "SELECT f.metadata,EXISTS(SELECT 1 FROM {} c WHERE c.field_id=f.field_id) AS canonical "
                "FROM {} f WHERE f.field_id=%s"
            ).format(self.fields.table("canonical_fields"), self.fields.table("fields")), (identifier,)).fetchone()
            if existing and not existing["canonical"]:
                rejected.append({"locator": candidate["locator"], "reason": "This identity is a reviewed alias; use its canonical field"})
                continue
            if existing and existing["metadata"].get("archived") is True:
                rejected.append({"locator": candidate["locator"], "reason": "This source identity is archived"})
                continue
            accepted.append({**candidate, "field_id": identifier,
                "candidate_id": fingerprint([row["import_id"], candidate["locator"], identifier]),
                "expected_version": existing["metadata"].get("workspace_version", 1) if existing else None,
                "action": "update" if existing else "create"})
        preview = {"candidates": accepted, "rejected": rejected}
        connection.execute("UPDATE workspace_imports SET preview=%s,preview_hash=%s WHERE import_id=%s",
                           (Jsonb(preview), fingerprint(preview), row["import_id"]))
        return {"import_id": row["import_id"], "valid": len(accepted), "rejected": len(rejected)}

    def apply_import(self, connection, job, row, content):
        preview = row["preview"]
        if preview is None or fingerprint(preview) != job["payload"]["preview_hash"]:
            raise WorkspaceError(409, "preview_changed", "The confirmed preview no longer matches")
        selected = [candidate for candidate in preview["candidates"]
                    if candidate["candidate_id"] in job["payload"]["candidate_ids"]]
        source_id = self.fields.save_asset(connection, row["filename"], content,
            MEDIA_TYPES[Path(row["filename"]).suffix.lower()[1:]], "explicitly_confirmed_import")
        results = []
        for candidate in sorted(selected, key=lambda item: item["field_id"]):
            identifier = candidate["field_id"]
            expected = candidate["expected_version"]
            if expected is None:
                metadata = {"workspace_version": 1, "archived": False}
                inserted = connection.execute(sql.SQL(
                    "INSERT INTO {}(field_id,project_id,source_identifier,metadata) VALUES (%s,%s,%s,%s) "
                    "ON CONFLICT DO NOTHING RETURNING field_id"
                ).format(self.fields.table("fields")), (identifier, row["project_id"],
                    "workspace:" + self.workspace_id + ":" + row["source_namespace"] + ":" + candidate["source_identifier"],
                    Jsonb(metadata))).fetchone()
                if inserted is None:
                    raise WorkspaceError(412, "version_conflict", "A previewed field was created by another submission")
            else:
                existing = self.fields.locked(connection, identifier)
                metadata = existing["metadata"]
                if metadata.get("workspace_version", 1) != expected:
                    raise WorkspaceError(412, "version_conflict", "A previewed field changed; create a new preview")
                metadata["workspace_version"] = expected + 1
            prepared = {**candidate, "properties": candidate["metadata"]}
            metadata.update(name=candidate["name"],
                current_boundary_id=self.fields.add_boundary(connection, identifier, source_id, prepared),
                geometry_provenance="user_imported; not surveyed or scientifically verified",
                import_provenance={"import_id": row["import_id"], "source_namespace": row["source_namespace"],
                                   "locator": candidate["locator"], "source_metadata": candidate["metadata"]})
            self.fields.write_metadata(connection, identifier, metadata)
            self.fields.revision(connection, identifier, metadata, job["job_id"])
            results.append(self.fields.result(identifier, metadata))
        return {"import_id": row["import_id"], "fields": results}
