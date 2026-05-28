# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_admin_token
from app.core.config import get_settings
from app.services.agents.iam.service_principal import ServicePrincipalService
from app.services.agents.iam.token_exchange import TokenExchangeService
from app.services.agents.iam.iam_audit import IAMAuditService
from app.models.agent_iam import AgentCredentialAuditEvent

def verify_iam_enabled():
    settings = get_settings()
    if not settings.agent_iam_enabled:
        raise HTTPException(status_code=403, detail="Agent IAM is disabled by feature flag.")

router = APIRouter(
    prefix="/admin/agents",
    tags=["agent-iam-admin"],
    dependencies=[Depends(verify_iam_enabled)]
)

# Schemas
class ServicePrincipalCreateRequest(BaseModel):
    description: Optional[str] = None

class ServicePrincipalResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    client_id: str
    description: Optional[str] = None
    status: str
    created_at: str
    client_secret: Optional[str] = None  # Raw secret, only returned on POST

class TokenGrantCreateRequest(BaseModel):
    tenant_id: str
    user_id: str
    connector_id: Optional[str] = None
    scopes: List[str]
    expires_at: Optional[float] = None  # epoch timestamp

class TokenGrantResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    user_id: str
    connector_id: Optional[str]
    scopes: List[str]
    is_revoked: bool
    created_at: str

class TokenExchangeRequest(BaseModel):
    tenant_id: str
    user_id: str
    connector_id: str
    requested_scopes: List[str]
    expires_in_seconds: int = 3600

class TokenExchangeResponse(BaseModel):
    token_id: uuid.UUID
    tenant_id: str
    agent_id: uuid.UUID
    token_type: str
    scopes: List[dict]
    expires_at: str
    raw_token: str

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: str
    agent_id: Optional[uuid.UUID]
    event_type: str
    actor_id: Optional[str]
    actor_type: Optional[str]
    details: dict
    created_at: str

# Endpoints
@router.post("/{id}/service-principal", response_model=ServicePrincipalResponse)
async def create_service_principal(
    id: uuid.UUID,
    payload: ServicePrincipalCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Creates a service principal for an agent."""
    tenant_id = "default"  # Default tenant context, in real app it would be extracted from token
    sp_service = ServicePrincipalService(db)
    try:
        sp, raw_secret = await sp_service.create_service_principal(
            tenant_id=tenant_id,
            agent_id=id,
            description=payload.description,
            actor_id="admin",
            actor_type="user"
        )
        await db.commit()
        return ServicePrincipalResponse(
            id=sp.id,
            tenant_id=sp.tenant_id,
            agent_id=sp.agent_id,
            client_id=sp.client_id,
            description=sp.description,
            status=sp.status,
            created_at=sp.created_at.isoformat(),
            client_secret=raw_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/{id}/service-principal", response_model=ServicePrincipalResponse)
async def get_service_principal(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Retrieves service principal metadata for an agent."""
    tenant_id = "default"
    sp_service = ServicePrincipalService(db)
    sp = await sp_service.get_service_principal(tenant_id, id)
    if not sp:
        raise HTTPException(status_code=404, detail="Service Principal not found for this agent.")
    return ServicePrincipalResponse(
        id=sp.id,
        tenant_id=sp.tenant_id,
        agent_id=sp.agent_id,
        client_id=sp.client_id,
        description=sp.description,
        status=sp.status,
        created_at=sp.created_at.isoformat()
    )

@router.post("/{id}/token-grants", response_model=TokenGrantResponse)
async def create_token_grant(
    id: uuid.UUID,
    payload: TokenGrantCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Creates a user delegated grant to let an agent use a connector."""
    exchange_service = TokenExchangeService(db)
    grant = await exchange_service.create_token_grant(
        tenant_id=payload.tenant_id,
        agent_id=id,
        user_id=payload.user_id,
        connector_id=payload.connector_id,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        actor_id="admin",
        actor_type="user"
    )
    await db.commit()
    return TokenGrantResponse(
        id=grant.id,
        tenant_id=grant.tenant_id,
        agent_id=grant.agent_id,
        user_id=grant.user_id,
        connector_id=grant.connector_id,
        scopes=grant.scopes,
        is_revoked=grant.is_revoked,
        created_at=grant.created_at.isoformat()
    )

@router.delete("/{id}/token-grants/{grant_id}")
async def revoke_token_grant(
    id: uuid.UUID,
    grant_id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Revokes a user delegated token grant."""
    exchange_service = TokenExchangeService(db)
    success = await exchange_service.revoke_token_grant(
        tenant_id=tenant_id,
        agent_id=id,
        grant_id=grant_id,
        actor_id="admin",
        actor_type="user"
    )
    if not success:
        raise HTTPException(status_code=404, detail="Token grant not found.")
    await db.commit()
    return {"status": "success", "message": "Token grant revoked."}

@router.post("/{id}/tokens/exchange", response_model=TokenExchangeResponse)
async def exchange_tokens(
    id: uuid.UUID,
    payload: TokenExchangeRequest,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Exchange user grant for an agent delegated token (OBO flow)."""
    exchange_service = TokenExchangeService(db)
    try:
        token, raw_token = await exchange_service.exchange_grant_for_token(
            tenant_id=payload.tenant_id,
            agent_id=id,
            user_id=payload.user_id,
            connector_id=payload.connector_id,
            requested_scopes=payload.requested_scopes,
            expires_in_seconds=payload.expires_in_seconds,
            actor_id=payload.user_id,
            actor_type="user"
        )
        await db.commit()
        return TokenExchangeResponse(
            token_id=token.id,
            tenant_id=token.tenant_id,
            agent_id=token.agent_id,
            token_type=token.token_type,
            scopes=token.scopes,
            expires_at=token.expires_at.isoformat(),
            raw_token=raw_token
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/iam/audit", response_model=List[AuditEventResponse])
async def list_audit_events(
    tenant_id: str = "default",
    agent_id: Optional[uuid.UUID] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
):
    """Retrieves IAM audit events."""
    stmt = select(AgentCredentialAuditEvent).where(
        AgentCredentialAuditEvent.tenant_id == tenant_id
    )
    if agent_id:
        stmt = stmt.where(AgentCredentialAuditEvent.agent_id == agent_id)
    stmt = stmt.order_by(AgentCredentialAuditEvent.created_at.desc()).limit(limit)

    res = await db.execute(stmt)
    events = res.scalars().all()
    return [
        AuditEventResponse(
            id=e.id,
            tenant_id=e.tenant_id,
            agent_id=e.agent_id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_type=e.actor_type,
            details=e.details,
            created_at=e.created_at.isoformat()
        )
        for e in events
    ]
