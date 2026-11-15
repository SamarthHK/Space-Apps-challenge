from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import Field, model_validator

from agri_data.workspace.errors import WorkspaceError
from .schemas import DTO, Meta


class JobFailure(DTO):
    code: str
    message: str
    retryable: bool


class Job(DTO):
    job_id: str
    resource_id: str
    kind: Literal["import_preview", "import_confirm", "export"]
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int
    result: dict | None
    error: JobFailure | None
    created_at: datetime
    updated_at: datetime


class JobResponse(DTO):
    data: Job
    meta: Meta


class ImportCandidate(DTO):
    candidate_id: str
    field_id: str
    source_identifier: str
    locator: str
    name: str | None
    action: Literal["create", "update"]
    expected_version: int | None
    geometry: dict
    original_geometry: dict
    metric_crs: str
    area_m2: float
    perimeter_m: float
    metadata: dict


class ImportRejection(DTO):
    locator: str
    reason: str


class BoundaryImport(DTO):
    import_id: str
    project_id: str
    source_namespace: str
    filename: str
    sha256: str
    preview_job_id: str
    preview_hash: str | None
    confirmed_job_id: str | None
    candidates: list[ImportCandidate]
    rejected: list[ImportRejection]


class ImportResponse(DTO):
    data: BoundaryImport
    meta: Meta


class ImportConfirmation(DTO):
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_ids: list[str] = Field(min_length=1, max_length=50)


class ExportField(DTO):
    field_id: str = Field(min_length=1, max_length=256)
    boundary_id: str = Field(min_length=1, max_length=256)


class ExportRequest(DTO):
    format: Literal["geojson", "kml", "kmz"]
    fields: list[ExportField] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_selections(self):
        if len({(item.field_id, item.boundary_id) for item in self.fields}) != len(self.fields):
            raise ValueError("Select each field/boundary pair only once")
        return self


router = APIRouter(prefix="/api/v1")


def envelope(request, data):
    return {"data": data, "meta": {"request_id": request.state.request_id, "api_version": "v1"}}


def submitted(request, response, job):
    response.headers["Location"] = "/api/v1/jobs/" + job["job_id"]
    return envelope(request, job)


@router.get("/jobs/{job_id}", operation_id="getJob", response_model=JobResponse)
def get_job(job_id: str, request: Request):
    return envelope(request, request.app.state.job_store.get(job_id))


@router.post("/imports", operation_id="createBoundaryImport", response_model=JobResponse, status_code=202,
             openapi_extra={"requestBody": {"required": True, "content": {
                 "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def create_import(request: Request, response: Response, filename: str = Query(..., max_length=160),
                        project_id: str = Query(..., min_length=1, max_length=200),
                        source_namespace: str = Query(..., min_length=1, max_length=80),
                        key: str | None = Header(None, alias="Idempotency-Key")):
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type not in {"application/octet-stream", "application/geo+json", "application/json",
                          "application/vnd.google-earth.kml+xml", "application/vnd.google-earth.kmz"}:
        raise WorkspaceError(415, "unsupported_media_type", "Send the original file bytes, not multipart or a filesystem path")
    content = await request.body()
    from starlette.concurrency import run_in_threadpool
    job = await run_in_threadpool(request.app.state.job_store.submit_import,
                                  content, filename, project_id, source_namespace, key)
    return submitted(request, response, job)


@router.get("/imports/{import_id}", operation_id="getBoundaryImport", response_model=ImportResponse)
def get_import(import_id: str, request: Request):
    return envelope(request, request.app.state.job_store.import_info(import_id))


@router.post("/imports/{import_id}/confirm", operation_id="confirmBoundaryImport",
             response_model=JobResponse, status_code=202)
def confirm_import(import_id: str, body: ImportConfirmation, request: Request, response: Response,
                   key: str | None = Header(None, alias="Idempotency-Key")):
    return submitted(request, response, request.app.state.job_store.confirm(
        import_id, body.model_dump(), key))


@router.post("/exports", operation_id="createExport", response_model=JobResponse, status_code=202)
def create_export(body: ExportRequest, request: Request, response: Response,
                  key: str | None = Header(None, alias="Idempotency-Key")):
    return submitted(request, response, request.app.state.job_store.submit_export(body.model_dump(), key))


@router.get("/exports/{export_id}/download", operation_id="downloadExport", response_class=Response,
            responses={200: {"content": {mime: {"schema": {"type": "string", "format": "binary"}} for mime in (
                "application/geo+json", "application/vnd.google-earth.kml+xml", "application/vnd.google-earth.kmz")}}})
def download_export(export_id: str, request: Request):
    record = request.app.state.job_store.download(export_id)
    return Response(content=bytes(record["content"]), media_type=record["media_type"], headers={
        "Content-Disposition": f'attachment; filename="{record["filename"]}"',
        "ETag": f'"sha256:{record["sha256"]}"',
    })
