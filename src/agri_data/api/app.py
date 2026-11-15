"""HTTP boundary without importing or executing the prototype pipeline."""

import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
import psycopg

from agri_data.services.database import DatabaseUnavailable, verify_schema

from .schemas import ErrorResponse
from .settings import ApiSettings

SCHEMA_VERSION = "1.0.0"


def error_response(request, status, code, message, field_errors=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "field_errors": field_errors or [],
                "request_id": request.state.request_id,
            }
        },
    )


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or ApiSettings()
    app = FastAPI(
        title="AgriData API",
        version=SCHEMA_VERSION,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Request-ID"],
        expose_headers=[
            "X-Request-ID", "X-API-Schema-Version", "Location",
            "Content-Disposition", "Retry-After",
        ],
    )

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", supplied) else uuid4().hex
        )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.max_request_bytes:
                response = error_response(
                    request, 413, "request_too_large", "Request body exceeds the limit"
                )
                break
        else:
            request._body = bytes(body)
            try:
                response = await call_next(request)
            except Exception:
                response = error_response(
                    request, 500, "internal_error", "The request could not be completed"
                )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-API-Schema-Version"] = SCHEMA_VERSION
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        origin = request.headers.get("origin")
        if origin in settings.allowed_origins and "access-control-allow-origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = (
                "X-Request-ID, X-API-Schema-Version, Location, Content-Disposition, Retry-After"
            )
            response.headers.append("Vary", "Origin")
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        fields = []
        for item in exc.errors():
            location = item["loc"]
            if location and location[0] in {"body", "query", "path", "header"}:
                location = location[1:]
            path = "/" + "/".join(
                str(part).replace("~", "~0").replace("/", "~1") for part in location
            )
            fields.append({"path": path, "code": item["type"], "message": item["msg"]})
        return error_response(request, 422, "validation_error", "Invalid request", fields)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(
            request, exc.status_code, "http_error",
            "Resource not found" if exc.status_code == 404 else "Request rejected",
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready(request: Request):
        try:
            verify_schema(settings)
        except (DatabaseUnavailable, psycopg.Error):
            return error_response(
                request, 503, "database_not_ready",
                "PostgreSQL and required migrations have not been verified",
            )
        return {"status": "ready"}

    @app.get("/api/v1/meta")
    def metadata():
        return {
            "api_version": "v1",
            "schema_version": SCHEMA_VERSION,
            "limits": {"max_request_bytes": settings.max_request_bytes},
            "capabilities": [
                {
                    "resource": resource, "implementation_status": "not_started",
                    "reason": "This capability is not implemented", "next_action": "Follow the implementation ledger",
                }
                for resource in [
                    "session", "profile", "fields", "analysis", "forecast",
                    "recommendations", "markets", "plans", "exports",
                ]
            ],
        }

    return app
