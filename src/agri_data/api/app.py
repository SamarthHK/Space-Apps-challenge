"""Separate-instance API with explicit shared or private-account access."""

import uuid
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from .config import Settings, request_id
from .schemas import (
    Capability, ErrorResponse, Health, HealthResponse, Meta, Workspace, WorkspaceResponse,
    FieldsResponse, FieldResponse, ObservationsResponse, ObservationResponse, EvidenceResponse,
)
from .data import DataStore, DataUnavailable, ResourceNotFound
from .pagination import Pagination, InvalidCursor, ChangedSnapshot
from .profile import router as profile_router
from .field_writes import router as field_router
from .workflows import router as workflow_router
from .auth import router as auth_router
from agri_data.workspace.accounts import AccountStore, require_csrf
from agri_data.workspace.settings import AccountSettings
from agri_data.workspace.fields import FieldStore, field_etag
from agri_data.workspace.jobs import JobStore
from agri_data.workspace.errors import WorkspaceError, WorkspaceUnavailable
from agri_data.workspace.store import WorkspaceStore


def error_response(request, status, code, message, *, details=None, retryable=False, headers=None):
    return JSONResponse(status_code=status, headers=headers, content={
        "error": {"code": code, "message": message, "details": details or [], "retryable": retryable},
        "meta": {"request_id": request.state.request_id, "api_version": "v1"},
    })


def create_app(settings=None, data_settings=None, workspace_settings=None, account_settings=None):
    if data_settings and workspace_settings and (
        data_settings.database == workspace_settings.database and data_settings.schema == workspace_settings.schema
    ):
        raise ValueError("Canonical data and shared application state require separate schemas")
    settings = settings or Settings.from_env()
    account_settings = account_settings or AccountSettings.from_env()
    private = account_settings.mode == "accounts"
    if private and any(urlsplit(item).hostname != settings.bind_host for item in settings.allowed_origins):
        raise ValueError("Private accounts require the same frontend/API hostname for SameSite cookies")
    revision = "private-workspace-2" if private else "shared-workspace-1"
    app = FastAPI(
        title="AgriData workspace API", version="1.0.0",
        docs_url=None, redoc_url=None, openapi_url="/api/v1/openapi.json",
        responses={code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 405, 409, 412, 413, 415, 422, 428, 429, 500, 503)},
    )
    store = DataStore(data_settings)
    app.state.data_store = store
    workspace_store = WorkspaceStore(workspace_settings)
    app.state.workspace_store = workspace_store
    field_store = FieldStore(workspace_store, data_settings)
    app.state.field_store = field_store
    job_store = JobStore(field_store)
    app.state.job_store = job_store
    account_store = AccountStore(workspace_store, data_settings, account_settings)
    app.state.account_store = account_store
    app.include_router(profile_router)
    app.include_router(field_router)
    app.include_router(workflow_router)
    app.include_router(auth_router)
    pagination = Pagination()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=private,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["X-Request-ID", "Content-Type", "If-Match", "Idempotency-Key", "X-CSRF-Token", "X-Account-ID"],
        expose_headers=["X-Request-ID", "ETag", "Location", "Content-Disposition"],
    )

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request.state.request_id = request_id(request.headers.get("X-Request-ID")) or uuid.uuid4().hex
        request.state.data_store = app.state.data_store
        request.state.workspace_store = app.state.workspace_store
        request.state.field_store = app.state.field_store
        request.state.job_store = app.state.job_store
        request.state.user = None
        try:
            host = request.url.hostname
            supplied_origin = request.headers.get("origin")
            if host not in settings.allowed_hosts:
                response = error_response(request, 400, "invalid_host", "Host is not configured for this API")
            elif supplied_origin is not None and supplied_origin not in settings.allowed_origins:
                response = error_response(request, 403, "origin_not_allowed", "Origin is not allowed")
            elif request.method in {"POST", "PATCH", "DELETE"} and supplied_origin is None:
                response = error_response(request, 403, "origin_required", "A configured browser Origin is required")
            else:
                public_paths = {
                    "/api/v1/health", "/api/v1/openapi.json", "/api/v1/auth/session",
                    "/api/v1/auth/bootstrap", "/api/v1/auth/register", "/api/v1/auth/login",
                }
                if private and request.method != "OPTIONS" and request.url.path not in public_paths:
                    token = request.cookies.get(account_store.session_cookie)
                    account = await run_in_threadpool(account_store.session, token)
                    expected_account = request.headers.get("X-Account-ID")
                    if expected_account is not None and expected_account != account["user_id"]:
                        raise WorkspaceError(409, "session_changed", "The signed-in account changed; reload this page")
                    if request.method in {"POST", "PATCH", "DELETE"}:
                        require_csrf(token, request.headers.get("X-CSRF-Token"))
                    scoped_fields = account_store.scoped_fields(account)
                    request.state.user = account["user_id"]
                    request.state.workspace_store = scoped_fields.workspace
                    request.state.field_store = scoped_fields
                    request.state.data_store = DataStore(scoped_fields.settings)
                    request.state.job_store = JobStore(scoped_fields, deployment_id=account_store.deployment_id)
                maximum = 16 * 1024 if request.url.path.startswith("/api/v1/auth/") else 16 * 1024 * 1024
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > maximum:
                        break
                if len(body) > maximum:
                    response = error_response(request, 413, "request_too_large", "Request exceeds the allowed size")
                else:
                    request._body = bytes(body)
                    response = await call_next(request)
        except WorkspaceError as error:
            response = error_response(request, error.status, error.code, error.message, headers=error.headers)
        except WorkspaceUnavailable as error:
            response = error_response(request, 503, "workspace_unavailable", str(error), retryable=True)
        except Exception:
            response = error_response(request, 500, "internal_error", "Request could not be completed")
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.headers.get("origin") in settings.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, ETag, Location, Content-Disposition"
            response.headers.add_vary_header("Origin")
            if private:
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        messages = {404: ("not_found", "Resource not found"), 405: ("method_not_allowed", "Method not allowed")}
        code, message = messages.get(error.status_code, ("request_failed", "Request could not be completed"))
        return error_response(request, error.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        details = [
            {"path": ".".join(map(str, item["loc"])), "code": item["type"], "message": "Invalid value"}
            for item in error.errors()
        ]
        return error_response(request, 422, "validation_error", "Request validation failed", details=details)

    @app.exception_handler(DataUnavailable)
    async def data_unavailable(request, error):
        return error_response(request, 503, "data_unavailable", str(error), retryable=True)

    @app.exception_handler(WorkspaceUnavailable)
    async def workspace_unavailable(request, error):
        return error_response(request, 503, "workspace_unavailable", str(error), retryable=True)

    @app.exception_handler(WorkspaceError)
    async def workspace_error(request, error):
        return error_response(request, error.status, error.code, error.message, headers=error.headers)

    @app.exception_handler(ResourceNotFound)
    async def resource_missing(request, error):
        return error_response(request, 404, "not_found", "Resource not found")

    @app.exception_handler(InvalidCursor)
    async def invalid_cursor(request, error):
        return error_response(request, 400, "invalid_cursor", "Restart pagination with the current filters")

    @app.exception_handler(ChangedSnapshot)
    async def changed_snapshot(request, error):
        return error_response(request, 409, "snapshot_changed", "Data changed; restart pagination")

    @app.get("/api/v1/health", operation_id="getHealth", response_model=HealthResponse)
    def health(request: Request):
        return HealthResponse(data=Health(contract_revision=revision), meta=Meta(request_id=request.state.request_id))

    @app.get("/api/v1/workspace", operation_id="getWorkspace", response_model=WorkspaceResponse)
    def workspace(request: Request):
        store = request.state.data_store
        workspace_store = request.state.workspace_store
        field_store = request.state.field_store
        job_store = request.state.job_store
        capabilities = [
            Capability(capability_id=name, state="not_implemented", operation_ids=operations,
                       reason="This capability has not been implemented")
            for name, operations in {
                "profile": ["getProfile", "updateProfile"],
                "fields": ["listFields", "getField"],
                "observations": ["listObservations", "getObservation", "listObservationEvidence"],
                "field_writes": ["createField", "updateField", "archiveField"],
                "analysis": ["getAnalysis", "listSoilRecords", "createSoilRecord"],
                "imports": ["createBoundaryImport", "getBoundaryImport", "confirmBoundaryImport"],
                "jobs": ["getJob"],
                "acquisition": ["createAcquisition"],
                "exports": ["createExport", "downloadExport"],
                "boundary_originals": ["downloadBoundaryImport", "downloadBoundaryOriginal"],
                "satellite": ["listScenes", "getVegetationSeries"],
                "crops": ["listCrops"],
                "recommendations": ["createRecommendation", "listRecommendations", "getRecommendation"],
                "markets": ["listMandis", "listMarkets"],
                "plans": ["listPlans", "createPlan", "getPlan", "updatePlan"],
            }.items()
        ]
        ready = store.available()
        writer_ready = field_store.ready()
        worker_ready = writer_ready and job_store.available()
        for capability in capabilities:
            if capability.capability_id in ("fields", "observations"):
                capability.state = "ready" if ready else "blocked"
                capability.reason = None if ready else "Explicit project data configuration and prepared database required"
            elif capability.capability_id == "profile":
                capability.state = "ready" if workspace_store.ready() else "blocked"
                capability.reason = None if capability.state == "ready" else "Configure and provision shared workspace storage"
            elif capability.capability_id == "field_writes":
                capability.state = "ready" if writer_ready else "blocked"
                capability.reason = None if capability.state == "ready" else "Scoped canonical storage and an authorized workspace writer required"
            elif capability.capability_id == "boundary_originals":
                capability.state = "ready" if writer_ready else "blocked"
                capability.reason = None if writer_ready else "Scoped field and original-asset storage required"
            elif capability.capability_id in ("imports", "exports"):
                capability.state = "ready" if worker_ready else "blocked"
                capability.reason = None if worker_ready else "A configured import/export worker heartbeat is required"
            elif capability.capability_id == "jobs":
                capability.state = "ready" if field_store.configured() and workspace_store.ready() else "blocked"
                capability.reason = None if capability.state == "ready" else "Configure scoped workspace job storage"
        return WorkspaceResponse(
            data=Workspace(project_ids=list(store.settings.project_ids) if store.settings else [],
                           capabilities=capabilities, contract_revision=revision,
                           access_mode="private_account" if private else "shared_trusted_network"),
            meta=Meta(request_id=request.state.request_id),
        )

    def page(request, rows, context, limit, cursor):
        context = [request.state.user, request.state.workspace_store.settings.workspace_id
                   if request.state.workspace_store.settings else None, *context]
        data, next_cursor = pagination.page(rows, context, limit, cursor)
        return {"data": data, "meta": {"request_id": request.state.request_id,
                                      "api_version": "v1", "next_cursor": next_cursor}}

    @app.get("/api/v1/fields", operation_id="listFields", response_model=FieldsResponse)
    def fields(request: Request, limit: int = Query(50, ge=1, le=200),
               cursor: str | None = Query(None, max_length=4096)):
        return page(request, request.state.data_store.fields(), ["fields"], limit, cursor)

    @app.get("/api/v1/fields/{field_id}", operation_id="getField", response_model=FieldResponse)
    def field_record(request: Request, response: Response, field_id: str, boundary_id: str | None = None):
        record, version = request.state.data_store.get_field_versioned(field_id, boundary_id)
        response.headers["ETag"] = field_etag(field_id, version)
        return {"data": record,
                "meta": {"request_id": request.state.request_id, "api_version": "v1"}}

    @app.get("/api/v1/fields/{field_id}/observations", operation_id="listObservations",
             response_model=ObservationsResponse)
    def observations(
        request: Request, field_id: str, variable_id: str | None = None,
        validation_status: Literal["all", "pending", "accepted", "rejected"] = "all",
        start_date: date | None = None, end_date: date | None = None,
        limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None, max_length=4096),
    ):
        if (start_date is None) != (end_date is None) or (start_date and start_date > end_date):
            return error_response(request, 422, "validation_error", "Provide an ordered start_date/end_date pair")
        rows = request.state.data_store.observations(field_id, variable_id, validation_status, start_date, end_date)
        context = [field_id, variable_id, validation_status, str(start_date), str(end_date)]
        return page(request, rows, context, limit, cursor)

    @app.get("/api/v1/fields/{field_id}/observations/{canonical_observation_id}",
             operation_id="getObservation", response_model=ObservationResponse)
    def observation(request: Request, field_id: str, canonical_observation_id: str):
        return {"data": request.state.data_store.observation(field_id, canonical_observation_id),
                "meta": {"request_id": request.state.request_id, "api_version": "v1"}}

    @app.get("/api/v1/fields/{field_id}/observations/{canonical_observation_id}/evidence",
             operation_id="listObservationEvidence", response_model=EvidenceResponse)
    def evidence(request: Request, field_id: str, canonical_observation_id: str,
                 limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None, max_length=4096)):
        return page(request, request.state.data_store.evidence(field_id, canonical_observation_id),
                    [field_id, canonical_observation_id, "evidence"], limit, cursor)

    return app
