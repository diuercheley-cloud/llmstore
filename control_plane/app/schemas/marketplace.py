import uuid

from pydantic import BaseModel, Field


class AgentManifest(BaseModel):
    name: str
    version: str
    author: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    tools_required: list[str] = Field(default_factory=list)
    models_required: list[str] = Field(default_factory=list)
    memory_required: bool = False
    network_required: bool = False
    license: str = "Proprietary"
    signature: str | None = None


class MarketplaceAgentRead(BaseModel):
    id: uuid.UUID
    publisher_id: uuid.UUID
    name: str
    version: str
    description: str
    is_verified: bool
    risk_level: str
    price_brl: float
    permissions: list[str]
    attestation_status: str


class InstallDryRunRequest(BaseModel):
    package_url: str


class InstallDryRunResponse(BaseModel):
    manifest: AgentManifest
    policy_evaluation: str  # allowed | blocked | needs_review
    warnings: list[str]
    estimated_revenue_share: float
    attestation_verified: bool


class ApproveInstallRequest(BaseModel):
    package_id: str
    confirmed_permissions: list[str]
