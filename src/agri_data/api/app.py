"""Read-only foundation; network isolation is not per-user authentication."""

import uuid
from datetime import date
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .config import Settings, request_id
from .schemas import (
    Capability, ErrorResponse, Health, HealthResponse, Meta, Workspace, WorkspaceResponse,
    FieldsResponse, FieldResponse, ObservationsResponse, ObservationResponse, EvidenceResponse,
)
from .data import DataStore, DataUnavailable, ResourceNotFound
from .pagination import Pagination, InvalidCursor, ChangedSnapshot


def error_response(request, status, code, message, *, details=None, retryable=False):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details or [], "retryable": retryable},
        "meta": {"request_id": request.state.request_id, "api_version": "v1"},
    })


def create_app(settings=None, data_settings=None):
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="AgriData shared workspace API", version="1.0.0",
        docs_url=None, redoc_url=None, openapi_url="/api/v1/openapi.json",
        responses={code: {"model": ErrorResponse} for code in (400, 403, 404, 405, 409, 422, 500, 503)},
    )
    store = DataStore(data_settings)
    pagination = Pagination()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request.state.request_id = request_id(request.headers.get("X-Request-ID")) or uuid.uuid4().hex
        try:
            host = request.url.hostname
            supplied_origin = request.headers.get("origin")
            if host not in settings.allowed_hosts:
                response = error_response(request, 400, "invalid_host", "Host is not configured for this API")
            elif supplied_origin is not None and supplied_origin not in settings.allowed_origins:
                response = error_response(request, 403, "origin_not_allowed", "Origin is not allowed")
            else:
                response = await call_next(request)
        except Exception:
            response = error_response(request, 500, "internal_error", "Request could not be completed")
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.headers.get("origin") in settings.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            response.headers.add_vary_header("Origin")
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
        return HealthResponse(data=Health(), meta=Meta(request_id=request.state.request_id))

    @app.get("/api/v1/workspace", operation_id="getWorkspace", response_model=WorkspaceResponse)
    def workspace(request: Request):
        capabilities = [
            Capability(capability_id=name, state="not_implemented", operation_ids=operations,
                       reason="This capability has not been implemented")
            for name, operations in {
                "profile": ["getProfile", "updateProfile"],
                "fields": ["listFields", "getField"],
                "observations": ["listObservations", "getObservation", "listObservationEvidence"],
                "field_writes": ["createField", "updateField"],
                "analysis": ["getAnalysis", "listSoilRecords", "createSoilRecord"],
                "imports": ["createBoundaryImport", "getBoundaryImport", "confirmBoundaryImport"],
                "jobs": ["getJob", "createAcquisition"],
                "exports": ["createExport", "downloadExport"],
                "satellite": ["listScenes", "getVegetationSeries"],
                "crops": ["listCrops"],
                "recommendations": ["createRecommendation", "listRecommendations", "getRecommendation"],
                "markets": ["listMandis", "listMarkets"],
                "plans": ["listPlans", "createPlan", "getPlan", "updatePlan"],
            }.items()
        ]
        ready = store.available()
        for capability in capabilities:
            if capability.capability_id in ("fields", "observations"):
                capability.state = "ready" if ready else "blocked"
                capability.reason = None if ready else "Explicit project data configuration and prepared database required"
        return WorkspaceResponse(
            data=Workspace(project_ids=list(data_settings.project_ids) if data_settings else [], capabilities=capabilities),
            meta=Meta(request_id=request.state.request_id),
        )

    def page(request, rows, context, limit, cursor):
        data, next_cursor = pagination.page(rows, context, limit, cursor)
        return {"data": data, "meta": {"request_id": request.state.request_id,
                                      "api_version": "v1", "next_cursor": next_cursor}}

    @app.get("/api/v1/fields", operation_id="listFields", response_model=FieldsResponse)
    def fields(request: Request, limit: int = Query(50, ge=1, le=200),
               cursor: str | None = Query(None, max_length=4096)):
        return page(request, store.fields(), ["fields"], limit, cursor)

    @app.get("/api/v1/fields/{field_id}", operation_id="getField", response_model=FieldResponse)
    def field_record(request: Request, field_id: str, boundary_id: str | None = None):
        return {"data": store.get_field(field_id, boundary_id),
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
        rows = store.observations(field_id, variable_id, validation_status, start_date, end_date)
        context = [field_id, variable_id, validation_status, str(start_date), str(end_date)]
        return page(request, rows, context, limit, cursor)

    @app.get("/api/v1/fields/{field_id}/observations/{canonical_observation_id}",
             operation_id="getObservation", response_model=ObservationResponse)
    def observation(request: Request, field_id: str, canonical_observation_id: str):
        return {"data": store.observation(field_id, canonical_observation_id),
                "meta": {"request_id": request.state.request_id, "api_version": "v1"}}

    @app.get("/api/v1/fields/{field_id}/observations/{canonical_observation_id}/evidence",
             operation_id="listObservationEvidence", response_model=EvidenceResponse)
    def evidence(request: Request, field_id: str, canonical_observation_id: str,
                 limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None, max_length=4096)):
        return page(request, store.evidence(field_id, canonical_observation_id),
                    [field_id, canonical_observation_id, "evidence"], limit, cursor)

    return app
