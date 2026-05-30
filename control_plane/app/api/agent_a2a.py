# Owner: agent-platform
# Surface: admin
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import require_admin
from app.services.agents.a2a.a2a_registry import A2ARegistryService
from app.services.agents.a2a.a2a_security import A2ASecurityService
from app.services.agents.a2a.a2a_server import A2AServerService

router = APIRouter(tags=["agent-a2a"])

# Request/Response schemas
class AgentA2ARegisterRequest(BaseModel):
    tenant_id: str = Field(..., max_length=128)
    agent_id: uuid.UUID
    auth_token: str = Field(..., max_length=256)
    target_url: Optional[str] = Field(None, max_length=512)
    capabilities: Optional[Dict[str, Any]] = None
    is_external: bool = False
    agent_name: Optional[str] = Field(None, max_length=128)

class AgentA2ARegistrationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    target_url: Optional[str]
    auth_token: str
    capabilities: Dict[str, Any]
    is_external: bool
    created_at: str
    updated_at: str

def to_registration_response(reg) -> AgentA2ARegistrationResponse:
    return AgentA2ARegistrationResponse(
        id=reg.id,
        tenant_id=reg.tenant_id,
        agent_id=reg.agent_id,
        target_url=reg.target_url,
        auth_token=reg.auth_token,
        capabilities=reg.capabilities or {},
        is_external=reg.is_external,
        created_at=reg.created_at.isoformat() if reg.created_at else "",
        updated_at=reg.updated_at.isoformat() if reg.updated_at else ""
    )

@router.get("/admin/agents/a2a/agents", response_model=List[AgentA2ARegistrationResponse])
async def list_a2a_agents(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
):
    A2ASecurityService.verify_a2a_enabled_or_raise()
    regs = await A2ARegistryService.list_registered_agents(db, tenant_id)
    return [to_registration_response(r) for r in regs]

@router.post("/admin/agents/a2a/register", response_model=AgentA2ARegistrationResponse)
async def register_a2a_agent(
    req: AgentA2ARegisterRequest,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
):
    A2ASecurityService.verify_a2a_enabled_or_raise()
    if req.is_external:
        A2ASecurityService.verify_external_enabled_or_raise()

    reg = await A2ARegistryService.register_agent(
        db=db,
        tenant_id=req.tenant_id,
        agent_id=req.agent_id,
        auth_token=req.auth_token,
        target_url=req.target_url,
        capabilities=req.capabilities,
        is_external=req.is_external,
        agent_name=req.agent_name
    )
    return to_registration_response(reg)

@router.post("/agents/a2a/message", tags=["client"])
async def receive_a2a_message(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    x_agent_a2a_token: Optional[str] = Header(None, alias="X-Agent-A2A-Token")
):
    A2ASecurityService.verify_a2a_enabled_or_raise()
    if not x_agent_a2a_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing A2A authentication token."
        )
    return await A2AServerService.receive_message(db, body, x_agent_a2a_token)

@router.post("/agents/a2a/delegate", tags=["client"])
async def delegate_a2a_task(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    x_agent_a2a_token: Optional[str] = Header(None, alias="X-Agent-A2A-Token")
):
    A2ASecurityService.verify_a2a_enabled_or_raise()
    if not x_agent_a2a_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing A2A authentication token."
        )
    return await A2AServerService.receive_delegation(db, body, x_agent_a2a_token)
