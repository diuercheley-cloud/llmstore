from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

_BLOCKED_HEARTBEAT_METADATA_KEYS = {
    "prompt",
    "prompts",
    "message",
    "messages",
    "document",
    "documents",
    "content",
    "payload",
    "attachment",
    "attachments",
}


class ManagedOrganizationBase(BaseModel):
    name: str
    slug: str


class ManagedOrganizationCreate(ManagedOrganizationBase):
    pass


class ManagedOrganization(ManagedOrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class ManagedWorkspaceBase(BaseModel):
    name: str
    slug: str


class ManagedWorkspaceCreate(ManagedWorkspaceBase):
    organization_id: UUID


class ManagedWorkspace(ManagedWorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_at: datetime


class ManagedApplianceBase(BaseModel):
    name: str


class ManagedApplianceCreate(ManagedApplianceBase):
    workspace_id: UUID
    appliance_external_id: str


class ManagedAppliance(ManagedApplianceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    appliance_external_id: str
    status: str
    version: str | None = None
    health_status: str | None = None
    readiness: bool = False
    last_heartbeat_at: datetime | None = None
    capacity_summary: dict[str, Any] | None = None
    enabled_providers: list[str] | None = None
    available_models: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class ApplianceEnrollmentToken(BaseModel):
    enrollment_token: str
    expires_at: datetime


class ApplianceEnrollRequest(BaseModel):
    enrollment_token: str
    appliance_external_id: str
    name: str


class ApplianceEnrollResponse(BaseModel):
    appliance_id: UUID
    workspace_id: UUID
    config: dict[str, Any]


class ApplianceHeartbeatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    health_status: str
    readiness: bool
    capacity_summary: dict[str, str | int | float | bool | None]
    enabled_providers: list[str]
    available_models: list[str]

    @field_validator("capacity_summary")
    @classmethod
    def validate_capacity_summary(cls, value: dict[str, str | int | float | bool | None]):
        for key, item in value.items():
            lowered = key.strip().lower()
            if lowered in _BLOCKED_HEARTBEAT_METADATA_KEYS:
                raise ValueError(
                    f"capacity_summary key '{key}' is not allowed in managed heartbeats"
                )
            if isinstance(item, str) and len(item) > 256:
                raise ValueError(f"capacity_summary value for '{key}' is too large")
        return value


class ManagedBillingAccount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    billing_email: str
    payment_method: str | None = None
    currency: str
    balance_cents: int
    created_at: datetime


class ManagedSupportCaseBase(BaseModel):
    subject: str
    description: str
    priority: str = "medium"


class ManagedSupportCaseCreate(ManagedSupportCaseBase):
    organization_id: UUID
    workspace_id: UUID | None = None
    appliance_id: UUID | None = None


class ManagedSupportCase(ManagedSupportCaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    workspace_id: UUID | None = None
    appliance_id: UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
