# Owner: agent-platform
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.agents import AgentToolInvocation
from app.services.agents import tool_registry as tool_service
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    model_config = ConfigDict(from_attributes=True)

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

class AgentToolInvocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ToolExecuteRequest(BaseModel):
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CredentialCreate(BaseModel):
    name: str = Field(..., max_length=128)
    credential_type: str = Field(..., max_length=32)
    raw_secret: str
    tenant_id: str = "default"
    expires_at: Optional[str] = None
    agent_tool_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None


class CredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    credential_type: str
    secret_masked: str
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    revoked: bool


class SideEffectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invocation_id: uuid.UUID
    tenant_id: str
    side_effect_level: str
    description: str
    resource_id: Optional[str] = None
    change_payload: Optional[Dict[str, Any]] = None
    created_at: str


class QuotaCounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    agent_id: Optional[uuid.UUID] = None
    agent_tool_id: Optional[uuid.UUID] = None
    side_effect_level: Optional[str] = None
    window_start: str
    window_end: str
    invocation_count: int
    max_limit: int


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


@router.post("/{id}/dry-run", dependencies=[Depends(verify_tool_registry_active)])
async def dry_run_agent_tool(
    id: uuid.UUID,
    payload: ToolExecuteRequest,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db_session)
):
    """Executes a dry-run invocation of a tool."""
    tool = await tool_service.get_tool(db, id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"AgentTool {id} not found.")
    
    from app.services.agents.tool_executor import execute_tool
    try:
        output = await execute_tool(
            db=db,
            tool=tool,
            parameters=payload.parameters,
            tenant_id=tenant_id,
            is_dry_run=True,
            executed_by="admin"
        )
        return output
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/execute", dependencies=[Depends(verify_tool_registry_active)])
async def execute_agent_tool(
    id: uuid.UUID,
    payload: ToolExecuteRequest,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db_session)
):
    """Executes a real invocation of a tool."""
    tool = await tool_service.get_tool(db, id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"AgentTool {id} not found.")
    
    from app.services.agents.tool_executor import execute_tool
    try:
        output = await execute_tool(
            db=db,
            tool=tool,
            parameters=payload.parameters,
            tenant_id=tenant_id,
            is_dry_run=False,
            executed_by="admin"
        )
        return output
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invocations/{id}/rollback", dependencies=[Depends(verify_tool_registry_active)])
async def rollback_invocation(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db_session)
):
    """Triggers manual rollback for the tool invocation."""
    from app.services.agents.tool_rollback import rollback_invocation_side_effects
    try:
        success = await rollback_invocation_side_effects(
            db=db,
            tenant_id=tenant_id,
            invocation_id=id
        )
        return {"success": success, "status": "rolled_back" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/side-effects", response_model=List[SideEffectResponse], dependencies=[Depends(verify_tool_registry_active)])
async def list_side_effects(
    tenant_id: str = "default",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieves captured side effects."""
    from app.models.agent_tool_execution import AgentToolSideEffect
    stmt = (
        select(AgentToolSideEffect)
        .where(AgentToolSideEffect.tenant_id == tenant_id)
        .order_by(AgentToolSideEffect.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    effects = res.scalars().all()
    
    return [
        SideEffectResponse(
            id=e.id,
            invocation_id=e.invocation_id,
            tenant_id=e.tenant_id,
            side_effect_level=e.side_effect_level,
            description=e.description,
            resource_id=e.resource_id,
            change_payload=e.change_payload,
            created_at=format_datetime(e.created_at)
        )
        for e in effects
    ]


@router.get("/credentials", response_model=List[CredentialResponse], dependencies=[Depends(verify_tool_registry_active)])
async def list_credentials(
    tenant_id: str = "default",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Lists registered credentials in masked format."""
    from app.models.agent_tool_execution import AgentToolCredential
    stmt = (
        select(AgentToolCredential)
        .where(AgentToolCredential.tenant_id == tenant_id)
        .order_by(AgentToolCredential.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    creds = res.scalars().all()
    
    return [
        CredentialResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            name=c.name,
            credential_type=c.credential_type,
            secret_masked=c.secret_masked,
            created_at=format_datetime(c.created_at),
            updated_at=format_datetime(c.updated_at),
            expires_at=format_datetime(c.expires_at) if c.expires_at else None,
            revoked=c.revoked
        )
        for c in creds
    ]


@router.post("/credentials", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_tool_registry_active)])
async def create_credential(
    payload: CredentialCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Registers a delegated credential and optionally grants it to a tool/agent."""
    from datetime import datetime

    from app.services.agents.tool_credentials import grant_credential, register_credential
    
    expires_dt = None
    if payload.expires_at:
        try:
            expires_dt = datetime.fromisoformat(payload.expires_at)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO format.")
            
    try:
        cred = await register_credential(
            db=db,
            tenant_id=payload.tenant_id,
            name=payload.name,
            credential_type=payload.credential_type,
            raw_secret=payload.raw_secret,
            expires_at=expires_dt
        )
        
        if payload.agent_tool_id:
            await grant_credential(
                db=db,
                tenant_id=payload.tenant_id,
                credential_id=cred.id,
                agent_tool_id=payload.agent_tool_id,
                agent_id=payload.agent_id,
                expires_at=expires_dt
            )
            
        await db.commit()
        return CredentialResponse(
            id=cred.id,
            tenant_id=cred.tenant_id,
            name=cred.name,
            credential_type=cred.credential_type,
            secret_masked=cred.secret_masked,
            created_at=format_datetime(cred.created_at),
            updated_at=format_datetime(cred.updated_at),
            expires_at=format_datetime(cred.expires_at) if cred.expires_at else None,
            revoked=cred.revoked
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/credentials/{id}/revoke", dependencies=[Depends(verify_tool_registry_active)])
async def revoke_tool_credential(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db_session)
):
    """Revokes a registered credential."""
    from app.services.agents.tool_credentials import revoke_credential
    try:
        success = await revoke_credential(db, tenant_id, id)
        if not success:
            raise HTTPException(status_code=404, detail="Credential not found or not owned by tenant.")
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/quotas", response_model=List[QuotaCounterResponse], dependencies=[Depends(verify_tool_registry_active)])
async def list_quotas(
    tenant_id: str = "default",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieves daily quota usage counters."""
    from app.models.agent_tool_execution import AgentToolQuotaCounter
    stmt = (
        select(AgentToolQuotaCounter)
        .where(AgentToolQuotaCounter.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    counters = res.scalars().all()
    
    return [
        QuotaCounterResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            agent_id=c.agent_id,
            agent_tool_id=c.agent_tool_id,
            side_effect_level=c.side_effect_level,
            window_start=format_datetime(c.window_start),
            window_end=format_datetime(c.window_end),
            invocation_count=c.invocation_count,
            max_limit=c.max_limit
        )
        for c in counters
    ]
