"""Lightweight reference request types; importing schemas never loads model dependencies."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReferenceContextNotFound(ValueError):
    pass


class ReferenceIntervalMismatch(ValueError):
    pass


class ReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    task: Literal["india_published_reference_suitability"]
    mode: Literal["historical_reference_analysis"]
    comparison_scope: Literal["reference_climate_only"]
    context_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    analysis_start: date
    analysis_end: date
    production_system: Literal["HRLM", "HILM", "LRLM", "LILM"]
    crop_ids: list[str]
    excluded_crop_ids: list[str] = Field(default_factory=list)
    minimum_reference_score: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.analysis_start > self.analysis_end:
            raise ValueError("Analysis interval is reversed")
        if len(set(self.crop_ids)) != len(self.crop_ids):
            raise ValueError("Repeated candidates would distort preference mass")
        return self
