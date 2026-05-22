import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.agents import tool_registry as tool_service
from app.models.agents import AgentToolInvocation

router = APIRouter(prefix="/admin/agent-tools", tags=["agent-tools-admin"])

def verify_tool_registry_active():
    settings = get_settings()
    if not settings.agent_tool_registry_enabled:
        raise HTTPException(
            status_code=400,
            detail="Agent tool registry is disabled. Set AGENT_TOOL_REGISTRY_ENABLED=true to enable it."
        )

# Pydantic Schemas
class AgentToolCreate(BaseModel):
    name: str = Field(..., max_length=128)
    version: Optional[str] = "0.1.0"
    description: Optional[str] = None
    category: str = Field(..., max_length=64)
    input_schema_json: Optional[dict] = None
    output_schema_json: Optional[dict] = None
    risk_level: Optional[str] = "low"
    side_effect_level: Optional[str] = "none"
    timeout_seconds: Optional[int] = 30
    retry_policy: Optional[dict] = None
    owner: Optional[str] = Field(None, max_length=128)
    enabled: Optional[bool] = None
    requires_approval: Optional[bool] = None
    dry_run_supported: Optional[bool] = False
    rollback_supported: Optional[bool] = False
    docs_url: Optional[str] = Field(None, max_length=256)
    data_boundary: Optional[str] = Field(None, max_length=64)

class AgentToolUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    version: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=64)
    input_schema_json: Optional[dict] = None
    output_schema_json: Optional[dict] = None
    risk_level: Optional[str] = None
    side_effect_level: Optional[str] = None
    timeout_seconds: Optional[int] = None
    retry_policy: Optional[dict] = None
    owner: Optional[str] = Field(None, max_length=128)
    enabled: Optional[bool] = None
    requires_approval: Optional[bool] = None
    dry_run_supported: Optional[bool] = None
    rollback_supported: Optional[bool] = None
    docs_url: Optional[str] = Field(None, max_length=256)
    data_boundary: Optional[str] = Field(None, max_length=64)

class AgentToolResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    description: Optional[str] = None
    category: str
    input_schema_json: dict
    output_schema_json: dict
    risk_level: str
    side_effect_level: str
    timeout_seconds: int
    retry_policy: Optional[dict] = None
    owner: Optional[str] = None
    enabled: bool
    requires_approval: bool
    dry_run_supported: bool
    rollback_supported: bool
    docs_url: Optional[str] = None
    data_boundary: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class AgentToolInvocationResponse(BaseModel):
    id: uuid.UUID
    agent_tool_id: uuid.UUID
    run_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    input_hash: str
    output_hash: Optional[str] = None
    status: str
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None
    executed_by: str
    is_dry_run: bool
    is_rollback: bool
    created_at: str

    class Config:
        from_attributes = True


# Helpers
def format_datetime(dt) -> str:
    return dt.isoformat() if dt else ""

def to_tool_response(tool) -> AgentToolResponse:
    return AgentToolResponse(
        id=tool.id,
        name=tool.name,
        version=tool.version,
        description=tool.description,
        category=tool.category,
        input_schema_json=tool.input_schema_json,
        output_schema_json=tool.output_schema_json,
        risk_level=tool.risk_level,
        side_effect_level=tool.side_effect_level,
        timeout_seconds=tool.timeout_seconds,
        retry_policy=tool.retry_policy,
        owner=tool.owner,
        enabled=tool.enabled,
        requires_approval=tool.requires_approval,
        dry_run_supported=tool.dry_run_supported,
        rollback_supported=tool.rollback_supported,
        docs_url=tool.docs_url,
        data_boundary=tool.data_boundary,
        created_at=format_datetime(tool.created_at),
        updated_at=format_datetime(tool.updated_at)
    )

def to_invocation_response(inv) -> AgentToolInvocationResponse:
    return AgentToolInvocationResponse(
        id=inv.id,
        agent_tool_id=inv.agent_tool_id,
        run_id=inv.run_id,
        agent_id=inv.agent_id,
        input_hash=inv.input_hash,
        output_hash=inv.output_hash,
        status=inv.status,
        latency_ms=inv.latency_ms,
        error_message=inv.error_message,
        executed_by=inv.executed_by,
        is_dry_run=inv.is_dry_run,
        is_rollback=inv.is_rollback,
        created_at=format_datetime(inv.created_at)
    )


# Endpoints
@router.get("", response_model=List[AgentToolResponse], dependencies=[Depends(verify_tool_registry_active)])
async def list_agent_tools(
    category: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Lists registered tools with optional filters."""
    tools = await tool_service.list_tools(db, limit, offset, category, enabled)
    return [to_tool_response(t) for t in tools]


@router.post("", response_model=AgentToolResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_tool_registry_active)])
async def register_agent_tool(
    payload: AgentToolCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Registers a new tool in the catalog."""
    try:
        tool = await tool_service.create_tool(db, payload.model_dump())
        return to_tool_response(tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{id}", response_model=AgentToolResponse, dependencies=[Depends(verify_tool_registry_active)])
async def update_agent_tool(
    id: uuid.UUID,
    payload: AgentToolUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Updates metadata and potentially registers a new version for an entry."""
    try:
        tool = await tool_service.update_tool(db, id, payload.model_dump(exclude_unset=True))
        return to_tool_response(tool)
    except ValueError as e:
        # Check if it was not found vs validation error
        existing = await tool_service.get_tool(db, id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"AgentTool {id} not found.")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/enable", response_model=AgentToolResponse, dependencies=[Depends(verify_tool_registry_active)])
async def enable_agent_tool(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Enables a tool in the registry."""
    try:
        tool = await tool_service.enable_tool(db, id)
        return to_tool_response(tool)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id}/disable", response_model=AgentToolResponse, dependencies=[Depends(verify_tool_registry_active)])
async def disable_agent_tool(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Disables a tool in the registry."""
    try:
        tool = await tool_service.disable_tool(db, id)
        return to_tool_response(tool)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{id}/invocations", response_model=List[AgentToolInvocationResponse], dependencies=[Depends(verify_tool_registry_active)])
async def list_tool_invocations(
    id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieves all version snapshots registered for a given tool."""
    tool = await tool_service.get_tool(db, id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"AgentTool {id} not found.")
    
    result = await db.execute(
        select(AgentToolInvocation)
        .where(AgentToolInvocation.agent_tool_id == id)
        .order_by(AgentToolInvocation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    invocations = result.scalars().all()
    return [to_invocation_response(inv) for inv in invocations]
