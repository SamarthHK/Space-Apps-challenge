"""Bounded reference-product inference, distinct from field recommendation runs."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import Field

from agri_data.contracts.india_inference_contract import ReferenceRequest

from .schemas import DTO, Meta, PageMeta


Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
CropID = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*:[A-Za-z0-9._-]+$")]
Score = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Preference = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
System = Literal["HRLM", "HILM", "LRLM", "LILM"]


class ReferencePredictionInput(ReferenceRequest):
    model_id: Digest
    crop_ids: list[CropID] = Field(max_length=100)
    excluded_crop_ids: list[CropID] = Field(default_factory=list, max_length=100)


class ReferencePeriod(DTO):
    period_id: str
    analysis_start: date
    analysis_end: date


class ReferenceCrop(DTO):
    crop_id: CropID
    display_name: str
    crop_group: str
    production_systems: list[System]


class ReferenceModelInfo(DTO):
    schema_version: Literal["1"]
    model_id: Digest
    dataset_id: Digest
    task: Literal["india_published_reference_suitability"]
    mode: Literal["historical_reference_analysis"]
    comparison_scope: Literal["reference_climate_only"]
    method: Literal["baseline", "catboost", "mlp"]
    reference_score_unit: Literal["GAEZ_suitability_index_rescaled_0_to_100"]
    preference_semantics: Literal["relative_GAEZ_reference_preference_not_probability_of_farming_success"]
    periods: list[ReferencePeriod]
    crops: list[ReferenceCrop]
    context_count: int = Field(ge=1)
    maximum_candidates: Literal[100]
    operational_recommendation_ready: Literal[False]
    rotation_effects_supported: Literal[False]
    preplant_supported: Literal[False]
    strict_as_of_supported: Literal[False]
    unassessed_requirement_axes: list[str]
    attribution: list[str]
    example_request: ReferencePredictionInput


class ReferenceContext(DTO):
    context_id: Digest
    site_id: str
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    analysis_start: date
    analysis_end: date
    period_id: str
    support: Literal["native_5_arcminute_GAEZ_reference_cell"]


class ReferenceEvidenceContext(ReferenceContext):
    nasa_support_ids: list[str]
    source_record_ids: dict[str, Digest]


class RankedReferenceCrop(DTO):
    crop_id: CropID
    display_name: str
    crop_group: str
    reference_score: Score
    relative_preference: Preference
    empirical_reference_error_band: tuple[Score, Score]
    missing_features: list[str]
    outside_training_numeric_range: list[str]
    unseen_categorical_features: list[str]


class WithheldReferenceCrop(DTO):
    crop_id: CropID
    reason: Literal["excluded_by_farmer", "no_target_bearing_training_support", "below_requested_reference_score"]
    relative_preference: Literal[0.0]
    reference_score: Score | None = None


class ReferencePrediction(DTO):
    schema_version: Literal["1"]
    status: Literal["scored_reference_context", "abstained"]
    reason: Literal["no_eligible_trained_candidates"] | None
    task: Literal["india_published_reference_suitability"]
    method: Literal["baseline", "catboost", "mlp"]
    model_id: Digest
    dataset_id: Digest
    context: ReferenceEvidenceContext
    production_system: System
    requested_candidates: list[CropID]
    candidate_set: list[CropID]
    ranked: list[RankedReferenceCrop]
    withheld: list[WithheldReferenceCrop]
    preference_semantics: Literal["relative_GAEZ_reference_preference_not_probability_of_farming_success"]
    calibration_scope: str
    reference_score_unit: Literal["GAEZ_suitability_index_rescaled_0_to_100"]
    operational_recommendation_ready: Literal[False]
    rotation_effects_supported: Literal[False]
    unassessed_requirement_axes: list[str]
    attribution: list[str]
    limitations: list[str]
    warnings: list[str]


class ReferenceModelResponse(DTO):
    data: ReferenceModelInfo
    meta: Meta


class ReferenceContextsResponse(DTO):
    data: list[ReferenceContext]
    meta: PageMeta


class ReferencePredictionResponse(DTO):
    data: ReferencePrediction
    meta: Meta


router = APIRouter(prefix="/api/v1/reference-model", tags=["reference suitability"])


@router.get("", operation_id="getReferenceModel", response_model=ReferenceModelResponse)
def model_info(request: Request):
    return {"data": request.app.state.reference_store.metadata(),
            "meta": {"request_id": request.state.request_id, "api_version": "v1"}}


@router.get("/contexts", operation_id="listReferenceContexts", response_model=ReferenceContextsResponse)
def reference_contexts(request: Request, model_id: Digest,
                       period_id: str | None = Query(None, min_length=1, max_length=32),
                       limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None, max_length=4096)):
    store = request.app.state.reference_store
    rows = store.contexts(model_id, period_id)
    data, next_cursor = store.pagination.page(rows, ["reference_contexts", model_id, period_id], limit, cursor)
    return {"data": data, "meta": {"request_id": request.state.request_id,
                                  "api_version": "v1", "next_cursor": next_cursor}}


@router.post("/predictions", operation_id="predictReferenceSuitability",
             response_model=ReferencePredictionResponse, response_model_exclude_unset=True,
             description="Stateless historical reference scoring, not a field recommendation or persisted job.")
def reference_prediction(body: ReferencePredictionInput, request: Request):
    return {"data": request.app.state.reference_store.predict(body.model_dump(mode="json")),
            "meta": {"request_id": request.state.request_id, "api_version": "v1"}}
