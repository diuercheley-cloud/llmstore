from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class AgentManifest(BaseModel):
    name: str
    version: str
    author: str
    description: str
    permissions: List[str] = Field(default_factory=list)
    tools_required: List[str] = Field(default_factory=list)
    models_required: List[str] = Field(default_factory=list)
    memory_required: bool = False
    network_required: bool = False
    license: str = "Proprietary"
    signature: Optional[str] = None


class MarketplaceAgentRead(BaseModel):
    id: uuid.UUID
    publisher_id: uuid.UUID
    name: str
    version: str
    description: str
    is_verified: bool
    risk_level: str
    price_brl: float
    permissions: List[str]
    attestation_status: str


class InstallDryRunRequest(BaseModel):
    package_url: str


class InstallDryRunResponse(BaseModel):
    manifest: AgentManifest
    policy_evaluation: str  # allowed | blocked | needs_review
    warnings: List[str]
    estimated_revenue_share: float
    attestation_verified: bool


class ApproveInstallRequest(BaseModel):
    package_id: str
    confirmed_permissions: List[str]
