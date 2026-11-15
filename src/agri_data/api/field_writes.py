from typing import Literal

from fastapi import APIRouter, Header, Request, Response
from pydantic import Field, model_validator

from agri_data.workspace.fields import field_etag
from agri_data.workspace.geometry import prepare_geometry
from .schemas import DTO, Meta


class FieldGeometry(DTO):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list

    @model_validator(mode="after")
    def valid_geometry(self):
        prepare_geometry(self.model_dump())
        return self


class FieldCreate(DTO):
    project_id: str = Field(min_length=1, max_length=200)
    name: str | None = Field(default=None, max_length=200)
    geometry: FieldGeometry


class FieldPatch(DTO):
    name: str | None = Field(default=None, max_length=200)
    geometry: FieldGeometry | None = None

    @model_validator(mode="after")
    def writable_changes(self):
        if not self.model_fields_set or ("geometry" in self.model_fields_set and self.geometry is None):
            raise ValueError("Supply a name change or valid geometry; geometry cannot be cleared")
        return self


class FieldMutation(DTO):
    field_id: str
    version: int = Field(ge=1)
    current_boundary_id: str | None
    archived: bool


class FieldMutationResponse(DTO):
    data: FieldMutation
    meta: Meta


router = APIRouter(prefix="/api/v1")


def result_response(request, response, result):
    response.headers["ETag"] = field_etag(result["field_id"], result["version"])
    return {"data": result, "meta": {"request_id": request.state.request_id, "api_version": "v1"}}


@router.post("/fields", operation_id="createField", response_model=FieldMutationResponse, status_code=201)
def create_field(body: FieldCreate, request: Request, response: Response,
                 key: str | None = Header(None, alias="Idempotency-Key")):
    result = request.app.state.field_store.create(body, key, request.state.request_id)
    response.headers["Location"] = "/api/v1/fields/" + result["field_id"]
    return result_response(request, response, result)


@router.patch("/fields/{field_id}", operation_id="updateField", response_model=FieldMutationResponse)
def update_field(field_id: str, body: FieldPatch, request: Request, response: Response,
                 etag: str | None = Header(None, alias="If-Match")):
    result = request.app.state.field_store.update(field_id, body, etag, request.state.request_id)
    return result_response(request, response, result)


@router.delete("/fields/{field_id}", operation_id="archiveField", response_model=FieldMutationResponse)
def archive_field(field_id: str, request: Request, response: Response,
                  etag: str | None = Header(None, alias="If-Match")):
    result = request.app.state.field_store.update(field_id, None, etag, request.state.request_id, archive=True)
    return result_response(request, response, result)
