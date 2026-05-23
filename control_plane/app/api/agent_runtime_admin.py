import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.agents import agent_state

router = APIRouter(prefix="/admin/agents", tags=["agent-runtime-admin"])

def verify_runtime_active():
    settings = get_settings()
    if not settings.agent_runtime_enabled:
        raise HTTPException(
            status_code=400,
            detail="Agent runtime is disabled. Set AGENT_RUNTIME_ENABLED=true to enable it."
        )

# Pydantic Schemas
class AgentDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=128)
    version: str = Field(..., max_length=64)
    description: Optional[str] = None
    instructions: str
    model_id: str = Field(..., max_length=128)
    owner: str = Field(..., max_length=128)
    tenant_id: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = "draft"
    risk_level: Optional[str] = "low"
    allowed_tools: Optional[List[str]] = None
    policy_id: Optional[str] = Field(None, max_length=128)
    memory_policy_id: Optional[str] = Field(None, max_length=128)
    max_steps: Optional[int] = 10
    max_runtime_seconds: Optional[int] = 300
    max_tokens: Optional[int] = None
    max_cost_brl: Optional[float] = None
    agent_class: Optional[str] = None

class AgentDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    model_id: Optional[str] = None
    owner: Optional[str] = None
    tenant_id: Optional[str] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    policy_id: Optional[str] = None
    memory_policy_id: Optional[str] = None
    max_steps: Optional[int] = None
    max_runtime_seconds: Optional[int] = None
    max_tokens: Optional[int] = None
    max_cost_brl: Optional[float] = None
    agent_class: Optional[str] = None

class AgentDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    description: Optional[str] = None
    instructions: str
    model_id: str
    owner: str
    tenant_id: Optional[str] = None
    status: str
    risk_level: str
    allowed_tools: Optional[List[str]] = None
    policy_id: Optional[str] = None
    memory_policy_id: Optional[str] = None
    max_steps: int
    max_runtime_seconds: int
    max_tokens: Optional[int] = None
    max_cost_brl: Optional[float] = None
    agent_class: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

def format_datetime(dt) -> str:
    return dt.isoformat() if dt else ""

def to_response(agent_def) -> AgentDefinitionResponse:
    return AgentDefinitionResponse(
        id=agent_def.id,
        name=agent_def.name,
        version=agent_def.version,
        description=agent_def.description,
        instructions=agent_def.instructions,
        model_id=agent_def.model_id,
        owner=agent_def.owner,
        tenant_id=agent_def.tenant_id,
        status=agent_def.status,
        risk_level=agent_def.risk_level,
        allowed_tools=agent_def.allowed_tools,
        policy_id=agent_def.policy_id,
        memory_policy_id=agent_def.memory_policy_id,
        max_steps=agent_def.max_steps,
        max_runtime_seconds=agent_def.max_runtime_seconds,
        max_tokens=agent_def.max_tokens,
        max_cost_brl=agent_def.max_cost_brl,
        agent_class=agent_def.agent_class,
        created_at=format_datetime(agent_def.created_at),
        updated_at=format_datetime(agent_def.updated_at),
    )

@router.get("", response_model=List[AgentDefinitionResponse], dependencies=[Depends(verify_runtime_active)])
async def get_agents(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    agents = await agent_state.list_agent_definitions(db, tenant_id)
    return [to_response(a) for a in agents]

@router.post("", response_model=AgentDefinitionResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_runtime_active)])
async def create_agent(
    payload: AgentDefinitionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    agent_def = await agent_state.create_agent_definition(db, payload.model_dump())
    return to_response(agent_def)

@router.patch("/{id}", response_model=AgentDefinitionResponse, dependencies=[Depends(verify_runtime_active)])
async def patch_agent(
    id: uuid.UUID,
    payload: AgentDefinitionUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    agent_def = await agent_state.get_agent_definition(db, id)
    if not agent_def:
        raise HTTPException(status_code=404, detail="Agent definition not found")
    
    updated = await agent_state.update_agent_definition(db, id, payload.model_dump(exclude_unset=True))
    return to_response(updated)

@router.post("/{id}/activate", response_model=AgentDefinitionResponse, dependencies=[Depends(verify_runtime_active)])
async def activate_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    agent_def = await agent_state.get_agent_definition(db, id)
    if not agent_def:
        raise HTTPException(status_code=404, detail="Agent definition not found")
        
    updated = await agent_state.update_agent_definition(db, id, {"status": "active"})
    return to_response(updated)

@router.post("/{id}/deprecate", response_model=AgentDefinitionResponse, dependencies=[Depends(verify_runtime_active)])
async def deprecate_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    agent_def = await agent_state.get_agent_definition(db, id)
    if not agent_def:
        raise HTTPException(status_code=404, detail="Agent definition not found")
        
    updated = await agent_state.update_agent_definition(db, id, {"status": "deprecated"})
    return to_response(updated)

@router.get("/slo/classes", dependencies=[Depends(verify_runtime_active)])
async def get_slo_classes():
    from app.services.agents.agent_budget import AgentBudgetService
    svc = AgentBudgetService()
    return svc._config.get("classes", {})

@router.get("/slo/report", dependencies=[Depends(verify_runtime_active)])
async def get_slo_report(
    agent_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_slo import AgentSLOService
    svc = AgentSLOService(db)
    if agent_id:
        return await svc.get_latest_slo(agent_id)
    return {"summary": "Agent SLO compliance report"}

@router.get("/budgets", dependencies=[Depends(verify_runtime_active)])
async def get_budgets():
    from app.services.agents.agent_budget import AgentBudgetService
    svc = AgentBudgetService()
    return svc._config.get("classes", {})

@router.post("/budgets/validate", dependencies=[Depends(verify_runtime_active)])
async def validate_budget(
    agent_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_budget import AgentBudgetService
    
    agent_def = await agent_state.get_agent_definition(db, agent_id)
    run = await agent_state.get_agent_run(db, run_id)
    
    if not agent_def or not run:
        raise HTTPException(status_code=404, detail="Agent or Run not found")
        
    svc = AgentBudgetService()
    is_valid, reason = await svc.validate_run_budget(agent_def, run)
    return {"is_valid": is_valid, "reason": reason}

@router.get("/incidents/playbooks", dependencies=[Depends(verify_runtime_active)])
async def list_playbooks(
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_incident_playbooks import AgentIncidentPlaybookService
    svc = AgentIncidentPlaybookService(db)
    return await svc.list_available_playbooks()

class PlaybookRunPayload(BaseModel):
    playbook_id: str
    confirmation: bool = False
    performed_by: str

@router.post("/incidents/{id}/run-playbook", dependencies=[Depends(verify_runtime_active)])
async def run_playbook(
    id: uuid.UUID,
    payload: PlaybookRunPayload,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_incident_playbooks import AgentIncidentPlaybookService
    svc = AgentIncidentPlaybookService(db)
    try:
        report = await svc.execute_playbook(
            id, 
            payload.playbook_id, 
            payload.performed_by, 
            payload.confirmation
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/catalog", dependencies=[Depends(verify_runtime_active)])
async def list_catalog(
    item_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_catalog import AgentCatalogService
    svc = AgentCatalogService(db)
    return await svc.list_items(item_type)

@router.get("/catalog/{id}/versions", dependencies=[Depends(verify_runtime_active)])
async def get_catalog_versions(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_catalog import AgentCatalogService
    svc = AgentCatalogService(db)
    return await svc.get_item_versions(id)

class CatalogPromotePayload(BaseModel):
    version_id: uuid.UUID
    performed_by: str

@router.post("/catalog/{id}/promote", dependencies=[Depends(verify_runtime_active)])
async def promote_catalog_item(
    id: uuid.UUID,
    payload: CatalogPromotePayload,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_catalog import AgentCatalogService
    svc = AgentCatalogService(db)
    try:
        return await svc.promote_to_production(id, payload.version_id, payload.performed_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class CatalogRollbackPayload(BaseModel):
    target_version_id: uuid.UUID
    performed_by: str
    reason: Optional[str] = None

@router.post("/catalog/{id}/rollback", dependencies=[Depends(verify_runtime_active)])
async def rollback_catalog_item(
    id: uuid.UUID,
    payload: CatalogRollbackPayload,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.agent_catalog import AgentCatalogService
    svc = AgentCatalogService(db)
    try:
        return await svc.rollback(id, payload.target_version_id, payload.performed_by, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class DelegationPolicyCreate(BaseModel):
    source_agent_id: uuid.UUID
    target_agent_id: uuid.UUID
    is_active: bool = True
    max_depth_override: Optional[int] = None
    requires_approval: bool = False

@router.post("/delegation-policies", dependencies=[Depends(verify_runtime_active)])
async def create_delegation_policy(
    payload: DelegationPolicyCreate,
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    from app.models.agents import AgentDelegationPolicy
    policy = AgentDelegationPolicy(
        tenant_id=tenant_id,
        source_agent_id=payload.source_agent_id,
        target_agent_id=payload.target_agent_id,
        is_active=payload.is_active,
        max_depth_override=payload.max_depth_override,
        requires_approval=payload.requires_approval
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

@router.get("/collaboration-sessions", dependencies=[Depends(verify_runtime_active)])
async def list_collaboration_sessions(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    from app.models.agents import AgentCollaborationSession
    res = await db.execute(select(AgentCollaborationSession).where(AgentCollaborationSession.tenant_id == tenant_id))
    return list(res.scalars().all())

@router.get("/collaboration-sessions/{id}/trace", dependencies=[Depends(verify_runtime_active)])
async def get_collaboration_trace(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    from app.services.agents.multi_agent_governance import MultiAgentGovernanceService
    svc = MultiAgentGovernanceService(db)
    return await svc.get_full_trace(id)
