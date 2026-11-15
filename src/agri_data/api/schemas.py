"""HTTP DTOs deliberately separate from internal scientific/storage records."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema

from agri_data.contracts.observation import Observation


# Provider-local timestamps (for example POWER LST) must not acquire a false UTC suffix.
ProviderTime = Annotated[datetime | None, WithJsonSchema({
    "anyOf": [
        {"type": "string", "pattern": (
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        )},
        {"type": "null"},
    ],
    "description": "Provider-local or offset timestamp; interpret with the record's timezone field.",
})]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Meta(DTO):
    request_id: str
    api_version: Literal["v1"] = "v1"


class ErrorDetail(DTO):
    path: str
    code: str
    message: str


class Error(DTO):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    retryable: bool = False


class ErrorResponse(DTO):
    error: Error
    meta: Meta


class Health(DTO):
    status: Literal["ok"] = "ok"
    contract_revision: Literal["shared-workspace-1", "private-workspace-2"] = "shared-workspace-1"


class HealthResponse(DTO):
    data: Health
    meta: Meta


class Capability(DTO):
    capability_id: str
    state: Literal["ready", "blocked", "not_implemented"]
    operation_ids: list[str]
    reason: str | None


class Workspace(DTO):
    access_mode: Literal["shared_trusted_network", "private_account"] = "shared_trusted_network"
    contract_revision: Literal["shared-workspace-1", "private-workspace-2"] = "shared-workspace-1"
    project_ids: list[str]
    capabilities: list[Capability]


class WorkspaceResponse(DTO):
    data: Workspace
    meta: Meta


class PageMeta(Meta):
    next_cursor: str | None


class BoundaryVersion(DTO):
    boundary_id: str
    source_asset_id: str


class FieldRecord(DTO):
    field_id: str
    project_id: str
    name: str | None
    current_boundary_id: str | None
    selected_boundary_id: str | None
    geometry_status: Literal["available", "selection_required", "unavailable"]
    boundary_versions: list[BoundaryVersion]
    geometry: dict[str, Any] | None
    metric_crs: str | None
    area_m2: float | None
    area_ha: float | None
    perimeter_m: float | None
    representative_point: dict[str, Any] | None
    repair_notes: str | None


class FieldResponse(DTO):
    data: FieldRecord
    meta: Meta


class FieldsResponse(DTO):
    data: list[FieldRecord]
    meta: PageMeta


class CanonicalObservation(DTO):
    canonical_observation_id: str
    context_id: str
    field_id: str
    variable_id: str
    validation_status: Literal["pending", "accepted", "rejected"]
    scientific_record: dict[str, Any]
    validation_evidence: dict[str, Any] | None
    evidence_count: int
    has_conflicting_revisions: bool


class ObservationsResponse(DTO):
    data: list[CanonicalObservation]
    meta: PageMeta


class ObservationResponse(DTO):
    data: CanonicalObservation
    meta: Meta


class EvidenceObservation(Observation):
    observed_at: ProviderTime = None
    period_start: ProviderTime = None
    period_end: ProviderTime = None


class EvidenceResponse(DTO):
    data: list[EvidenceObservation]
    meta: PageMeta
