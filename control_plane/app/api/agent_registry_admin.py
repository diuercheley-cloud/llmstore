import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import require_admin
from app.services.agents import agent_registry as reg_service
from app.services.agents import agent_lifecycle as lifecycle_service

router = APIRouter(prefix="/admin/agent-registry", tags=["agent-registry-admin"])

# Pydantic Schemas
class AgentRegistryEntryCreate(BaseModel):
    name: str = Field(..., max_length=128)
    semantic_version: Optional[str] = "0.1.0"
    owner: Optional[str] = Field(None, max_length=128)
    business_purpose: Optional[str] = None
    supported_surface_status: Optional[str] = "internal"
    risk_level: Optional[str] = "low"
    approval_required: Optional[bool] = False
    allowed_tenants: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    memory_enabled: Optional[bool] = False
    compliance_tags: Optional[List[str]] = None
    eval_baseline: Optional[str] = None
    instructions: Optional[str] = None

class AgentRegistryEntryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    semantic_version: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=128)
    business_purpose: Optional[str] = None
    supported_surface_status: Optional[str] = None
    risk_level: Optional[str] = None
    approval_required: Optional[bool] = None
    allowed_tenants: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None
    compliance_tags: Optional[List[str]] = None
    eval_baseline: Optional[str] = None
    instructions: Optional[str] = None

class AgentApprovalRequest(BaseModel):
    approved_by: str = Field(..., max_length=128)
    metadata: Optional[dict] = None

class AgentDeprecationRequest(BaseModel):
    reason: str
    replacement_agent_id: Optional[uuid.UUID] = None

class AgentRegistryEntryResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    semantic_version: str
    owner: Optional[str] = None
    business_purpose: Optional[str] = None
    supported_surface_status: str
    risk_level: str
    approval_required: bool
    allowed_tenants: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None
    memory_enabled: bool
    human_approval_required: bool
    compliance_tags: Optional[List[str]] = None
    status: str
    eval_baseline: Optional[str] = None
    instructions: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class AgentVersionResponse(BaseModel):
    id: uuid.UUID
    agent_registry_id: uuid.UUID
    semantic_version: str
    instructions: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    allowed_models: Optional[List[str]] = None
    created_at: str

    class Config:
        from_attributes = True


# Helpers
def format_datetime(dt) -> str:
    return dt.isoformat() if dt else ""

def to_registry_response(entry) -> AgentRegistryEntryResponse:
    return AgentRegistryEntryResponse(
        id=entry.id,
        agent_id=entry.agent_id,
        name=entry.name,
        semantic_version=entry.semantic_version,
        owner=entry.owner,
        business_purpose=entry.business_purpose,
        supported_surface_status=entry.supported_surface_status,
        risk_level=entry.risk_level,
        approval_required=entry.approval_required,
        allowed_tenants=entry.allowed_tenants,
        allowed_models=entry.allowed_models,
        allowed_tools=entry.allowed_tools,
        memory_enabled=entry.memory_enabled,
        human_approval_required=entry.human_approval_required,
        compliance_tags=entry.compliance_tags,
        status=entry.status,
        eval_baseline=entry.eval_baseline,
        instructions=entry.instructions,
        created_at=format_datetime(entry.created_at),
        updated_at=format_datetime(entry.updated_at),
    )

def to_version_response(version) -> AgentVersionResponse:
    return AgentVersionResponse(
        id=version.id,
        agent_registry_id=version.agent_registry_id,
        semantic_version=version.semantic_version,
        instructions=version.instructions,
        allowed_tools=version.allowed_tools,
        allowed_models=version.allowed_models,
        created_at=format_datetime(version.created_at),
    )


# Endpoints
@router.get("", response_model=List[AgentRegistryEntryResponse])
async def list_agent_registry(
    status: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Lists versioned agent registry entries with filtering."""
    entries = await reg_service.get_registry_entries(db, limit, offset, status, owner)
    return [to_registry_response(e) for e in entries]

@router.post("", response_model=AgentRegistryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_registry_entry(
    payload: AgentRegistryEntryCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Creates a new catalog entry in draft status."""
    try:
        entry = await reg_service.create_registry_entry(db, payload.model_dump(), performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=AgentRegistryEntryResponse)
async def get_agent_registry_entry(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Fetches details for a specific agent registry entry."""
    entry = await reg_service.get_registry_entry(db, id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Agent registry entry {id} not found.")
    return to_registry_response(entry)

@router.patch("/{id}", response_model=AgentRegistryEntryResponse)
async def update_agent_registry_entry(
    id: uuid.UUID,
    payload: AgentRegistryEntryUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Updates metadata and potentially registers a new version for an entry."""
    try:
        entry = await reg_service.update_registry_entry(db, id, payload.model_dump(exclude_unset=True), performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/submit-review", response_model=AgentRegistryEntryResponse)
async def submit_agent_review(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from draft -> review."""
    try:
        entry = await lifecycle_service.submit_review(db, id, performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/approve", response_model=AgentRegistryEntryResponse)
async def approve_agent_registry_entry(
    id: uuid.UUID,
    payload: AgentApprovalRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from review -> approved. Enforces risk-level rules."""
    try:
        entry = await lifecycle_service.approve_agent(
            db, id, approved_by=payload.approved_by, metadata=payload.metadata, performed_by="admin"
        )
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/activate", response_model=AgentRegistryEntryResponse)
async def activate_agent_registry_entry(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from approved/paused -> active. Enforces governance gates."""
    try:
        entry = await lifecycle_service.activate_agent(db, id, performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/pause", response_model=AgentRegistryEntryResponse)
async def pause_agent_registry_entry(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from active -> paused."""
    try:
        entry = await lifecycle_service.pause_agent(db, id, performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/deprecate", response_model=AgentRegistryEntryResponse)
async def deprecate_agent_registry_entry(
    id: uuid.UUID,
    payload: AgentDeprecationRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from active -> deprecated."""
    try:
        entry = await lifecycle_service.deprecate_agent(
            db, id, reason=payload.reason, replacement_id=payload.replacement_agent_id, performed_by="admin"
        )
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/archive", response_model=AgentRegistryEntryResponse)
async def archive_agent_registry_entry(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Transitions status from deprecated -> archived."""
    try:
        entry = await lifecycle_service.archive_agent(db, id, performed_by="admin")
        return to_registry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}/versions", response_model=List[AgentVersionResponse])
async def get_agent_registry_versions(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieves all semantic versions registered for a given agent entry."""
    versions = await reg_service.get_agent_versions(db, id)
    return [to_version_response(v) for v in versions]

@router.get("/{id}/policy-diff")
async def get_agent_policy_diff(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> Dict[str, Any]:
    return {
        "agent_id": str(id),
        "policy_diff": {
            "instructions": {"old": "", "new": ""},
            "allowed_tools": {"old": [], "new": []},
            "memory_policy": {"old": {}, "new": {}}
        }
    }

@router.get("/{id}/lineage")
async def get_agent_lineage(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> Dict[str, Any]:
    return {
        "agent_id": str(id),
        "versions": [],
        "promotions": [],
        "eval_baselines": [],
        "policy_changes": []
    }

@router.post("/{id}/promote")
async def promote_agent(
    id: uuid.UUID,
    target_status: str = Body(..., embed=True),
    reason: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> Dict[str, Any]:
    # Promotion check logic
    # 1. Eval pass?
    # 2. Approval?
    # 3. No critical incidents?
    return {
        "agent_id": str(id),
        "new_status": target_status,
        "promotion_id": str(uuid.uuid4())
    }
