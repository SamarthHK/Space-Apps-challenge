"""HTTP DTOs deliberately separate from internal scientific/storage records."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    contract_revision: Literal["shared-workspace-1"] = "shared-workspace-1"


class HealthResponse(DTO):
    data: Health
    meta: Meta


class Capability(DTO):
    capability_id: str
    state: Literal["ready", "blocked", "not_implemented"]
    operation_ids: list[str]
    reason: str | None


class Workspace(DTO):
    access_mode: Literal["shared_trusted_network"] = "shared_trusted_network"
    contract_revision: Literal["shared-workspace-1"] = "shared-workspace-1"
    project_ids: list[str]
    capabilities: list[Capability]


class WorkspaceResponse(DTO):
    data: Workspace
    meta: Meta
