from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Header, Request, Response
from pydantic import Field, field_validator, model_validator

from agri_data.workspace.store import profile_etag
from .schemas import DTO, Meta


class ProfileFields(DTO):
    name: str | None = Field(default=None, max_length=200)
    kannada_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    village: str | None = Field(default=None, max_length=200)
    taluk: str | None = Field(default=None, max_length=200)
    district: str | None = Field(default=None, max_length=200)
    state: str | None = Field(default=None, max_length=200)
    soil_health_card_no: str | None = Field(default=None, max_length=100)
    farmer_category: Literal["small_marginal", "medium", "large"] | None = None
    preferred_language: Literal["en", "kn"] | None = None
    risk_tolerance: Literal["conservative", "balanced", "progressive"] | None = None
    primary_objective: Literal["profit_maximization", "low_water_risk", "household_security"] | None = None

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        if value is not None and (
            not 7 <= sum(char.isdigit() for char in value) <= 15
            or any(char not in "+- ()0123456789" for char in value) or "+" in value[1:]
        ):
            raise ValueError("Enter a valid contact phone number or null")
        return value


class ProfilePatch(ProfileFields):
    @model_validator(mode="after")
    def not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Supply at least one profile property")
        return self


class SharedProfile(ProfileFields):
    workspace_id: str
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class ProfileResponse(DTO):
    data: SharedProfile
    meta: Meta


router = APIRouter(prefix="/api/v1")


@router.get("/profile", operation_id="getProfile", response_model=ProfileResponse)
def profile(request: Request, response: Response):
    result = request.app.state.workspace_store.get_profile()
    response.headers["ETag"] = profile_etag(result)
    return {"data": result, "meta": {"request_id": request.state.request_id, "api_version": "v1"}}


@router.patch("/profile", operation_id="updateProfile", response_model=ProfileResponse)
def update_profile(body: ProfilePatch, request: Request, response: Response,
                   if_match: str | None = Header(None, alias="If-Match")):
    result = request.app.state.workspace_store.update_profile(body, if_match, request.state.request_id)
    response.headers["ETag"] = profile_etag(result)
    return {"data": result, "meta": {"request_id": request.state.request_id, "api_version": "v1"}}
