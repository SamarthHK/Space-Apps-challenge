"""Typed observation transport contract from Plan.md section 4.2.

Schema validity alone is not scientific acceptance. Registered dimensions,
independent source validation, PostgreSQL readback and export checks remain gates.
"""

from datetime import date, datetime
from enum import Enum
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceType(str, Enum):
    measured = "measured"
    surveyed = "surveyed"
    published_parameter = "published_parameter"
    published_recommendation = "published_recommendation"
    satellite = "satellite"
    modelled_product = "modelled_product"
    reanalysis = "reanalysis"
    projection = "projection"
    derived = "derived"


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: Literal["1"]
    observation_id: str = Field(min_length=1)
    feature_id: str = Field(pattern=r"^F\d{2}-\d{3}$")
    variable_id: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    field_id: str | None = None
    region_id: str | None = None
    geometry_ref: str | None = None
    value_numeric: float | None = Field(default=None, strict=True)
    value_text: str | None = None
    value_boolean: bool | None = Field(default=None, strict=True)
    value_date: date | None = None
    value_geometry: dict[str, Any] | None = None
    value_series_ref: str | None = None
    original_value: Any = None
    original_unit: str | None = None
    standardized_unit: str = Field(min_length=1)
    measurement_basis: str = Field(min_length=1)
    observed_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    unknown_time_reason: str | None = None
    timezone: str | None = None
    temporal_resolution: str | None = None
    depth_top_cm: float | None = Field(default=None, ge=0)
    depth_bottom_cm: float | None = Field(default=None, gt=0)
    sample_id: str | None = None
    sensor_id: str | None = None
    crop_id: str | None = None
    cultivar_id: str | None = None
    growth_stage_id: str | None = None
    trial_id: str | None = None
    treatment_id: str | None = None
    season_id: str | None = None
    analyte: str | None = None
    statistic: str | None = None
    scenario_id: str | None = None
    ensemble_member: str | None = None
    reference_period: str | None = None
    evidence_type: EvidenceType
    source_id: str | None = None
    dataset_id: str | None = None
    source_binding_id: str | None = None
    source_asset_id: str | None = None
    source_record_locator: str | None = None
    extraction_method: str = Field(min_length=1)
    spatial_support: str = Field(min_length=1)
    spatial_resolution_m: float | None = Field(default=None, gt=0)
    native_crs: str | None = None
    coverage_geometry_ref: str | None = None
    valid_pixel_count: int | None = Field(default=None, ge=0, strict=True)
    spatial_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    temporal_coverage_percent: float | None = Field(default=None, ge=0, le=100)
    sample_count: int | None = Field(default=None, ge=0, strict=True)
    uncertainty: float | None = Field(default=None, ge=0)
    uncertainty_unit: str | None = None
    uncertainty_method: str | None = None
    quality_flags: list[str]
    validation_status: Literal["pending", "accepted", "rejected"]
    censoring_qualifier: str | None = None
    detection_limit: float | None = None
    detection_limit_unit: str | None = None
    parent_observation_ids: list[str]
    method_id: str | None = None
    processing_version: str = Field(min_length=1)
    extraction_job_id: str = Field(min_length=1)
    retrieved_at: datetime | None = None
    created_at: datetime
    raw_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_context(self):
        values = (
            self.value_numeric, self.value_text, self.value_boolean,
            self.value_date, self.value_geometry, self.value_series_ref,
        )
        if sum(value is not None for value in values) != 1:
            raise ValueError("A present observation must have exactly one typed value; missing values belong in feature status")
        if (self.depth_top_cm is None) != (self.depth_bottom_cm is None):
            raise ValueError("Depth bounds must be supplied together")
        if self.depth_top_cm is not None and self.depth_top_cm >= self.depth_bottom_cm:
            raise ValueError("Depth bottom must exceed depth top")
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("Period bounds must be supplied together")
        if self.period_start is not None and self.period_start > self.period_end:
            raise ValueError("Period end must not precede period start")
        if self.observed_at is None and self.period_start is None and not self.unknown_time_reason:
            raise ValueError("Unknown observation time needs an explicit reason")
        if self.evidence_type == EvidenceType.derived:
            if not self.parent_observation_ids or not self.method_id:
                raise ValueError("Derived observations require parents and a registered method")
        else:
            required = (
                self.original_value, self.original_unit, self.source_id, self.dataset_id,
                self.source_binding_id, self.source_asset_id, self.source_record_locator,
                self.retrieved_at, self.raw_sha256,
            )
            if any(value is None or value == "" for value in required):
                raise ValueError("Source observations require original representation and exact raw provenance")
        if self.censoring_qualifier:
            if self.detection_limit is None or not self.detection_limit_unit:
                raise ValueError("Censored records require a detection limit and unit")
            if self.value_numeric is not None:
                raise ValueError("Use the reported qualifier as text, not an invented censored concentration")
        if self.uncertainty is not None and (not self.uncertainty_unit or not self.uncertainty_method):
            raise ValueError("Uncertainty requires its unit and method")
        if self.evidence_type == EvidenceType.projection:
            if not all((self.scenario_id, self.ensemble_member, self.reference_period)):
                raise ValueError("Projections require scenario, ensemble member and reference period")
        _finite_tree(self.model_dump())
        return self


def _finite_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite values are forbidden, including nested source/geometry metadata")
    if isinstance(value, dict):
        for child in value.values():
            _finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            _finite_tree(child)
