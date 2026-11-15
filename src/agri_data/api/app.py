"""Read-only foundation; network isolation is not per-user authentication."""

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .config import Settings, request_id
from .schemas import (
    Capability, ErrorResponse, Health, HealthResponse, Meta, Workspace, WorkspaceResponse,
)


def error_response(request, status, code, message, *, details=None, retryable=False):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details or [], "retryable": retryable},
        "meta": {"request_id": request.state.request_id, "api_version": "v1"},
    })


def create_app(settings=None):
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="AgriData shared workspace API", version="1.0.0",
        docs_url=None, redoc_url=None, openapi_url="/api/v1/openapi.json",
        responses={code: {"model": ErrorResponse} for code in (400, 403, 404, 405, 422, 500, 503)},
    )
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
        return WorkspaceResponse(
            data=Workspace(project_ids=[], capabilities=capabilities),
            meta=Meta(request_id=request.state.request_id),
        )

    return app
