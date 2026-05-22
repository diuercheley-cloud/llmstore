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
