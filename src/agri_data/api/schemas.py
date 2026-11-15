"""Transport schemas; these contain no agricultural defaults."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldError(StrictModel):
    path: str
    code: str
    message: str


class ErrorDetail(StrictModel):
    code: str
    message: str
    field_errors: list[FieldError] = Field(default_factory=list)
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail


class ProfilePatch(StrictModel):
    version: int = Field(ge=1, strict=True)
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
    primary_objective: Literal[
        "profit_maximization", "low_water_risk", "household_security"
    ] | None = None

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value is not None:
            digits = "".join(char for char in value if char.isdigit())
            if (
                not 7 <= len(digits) <= 15
                or any(char not in "+- ()0123456789" for char in value)
                or "+" in value[1:]
            ):
                raise ValueError("Enter a valid contact phone number or null")
        return value
