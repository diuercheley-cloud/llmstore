# Owner: agent-platform
import hashlib
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_secret
from app.core.time import utc_now
from app.models.agent_mcp_oauth import (
    AgentMCPOAuthClient,
    AgentMCPDelegatedGrant,
    AgentMCPScopePolicy,
)


class MCPOAuthAuditLog:
    events: list[dict] = []

    @classmethod
    def record(
        cls,
        grant_id: str | None,
        scopes: list[str],
        user_id: str | None,
        tenant_id: str,
        mcp_server: str,
        tool: str | None,
        policy_decision: str,
    ) -> dict:
        user_id_hash = hashlib.sha256(user_id.encode()).hexdigest() if user_id else "none"
        tenant_id_hash = hashlib.sha256(tenant_id.encode()).hexdigest()
        event = {
            "grant_id": str(grant_id) if grant_id else "global",
            "scope": scopes,
            "user_id_hash": user_id_hash,
            "tenant_id_hash": tenant_id_hash,
            "mcp_server": mcp_server,
            "tool": tool or "none",
            "policy_decision": policy_decision,
            "timestamp": utc_now().isoformat(),
        }
        cls.events.append(event)
        return event


async def create_mcp_oauth_client(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    client_id: str,
    client_secret: str,
    auth_url: str | None,
    token_url: str | None,
    default_scopes: list[str],
) -> AgentMCPOAuthClient:
    client = AgentMCPOAuthClient(
        tenant_id=tenant_id,
        name=name,
        client_id=client_id,
        client_secret_hash=hash_secret(client_secret),
        auth_url=auth_url,
        token_url=token_url,
        default_scopes=default_scopes,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def list_mcp_oauth_clients(db: AsyncSession, tenant_id: str) -> list[AgentMCPOAuthClient]:
    result = await db.execute(select(AgentMCPOAuthClient).where(AgentMCPOAuthClient.tenant_id == tenant_id))
    return list(result.scalars().all())


async def create_mcp_delegated_grant(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    agent_id: uuid.UUID | None,
    mcp_server: str,
    access_token: str,
    refresh_token: str | None,
    scopes: list[str],
    expires_at: datetime | None,
) -> AgentMCPDelegatedGrant:
    grant = AgentMCPDelegatedGrant(
        tenant_id=tenant_id,
        user_id=user_id,
        agent_id=agent_id,
        mcp_server=mcp_server,
        access_token=access_token,
        refresh_token=refresh_token,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return grant


async def list_mcp_delegated_grants(db: AsyncSession, tenant_id: str) -> list[AgentMCPDelegatedGrant]:
    result = await db.execute(select(AgentMCPDelegatedGrant).where(AgentMCPDelegatedGrant.tenant_id == tenant_id))
    return list(result.scalars().all())


async def delete_mcp_delegated_grant(db: AsyncSession, grant_id: uuid.UUID, tenant_id: str) -> bool:
    result = await db.execute(
        select(AgentMCPDelegatedGrant).where(
            AgentMCPDelegatedGrant.id == grant_id,
            AgentMCPDelegatedGrant.tenant_id == tenant_id
        )
    )
    grant = result.scalar_one_or_none()
    if grant:
        await db.delete(grant)
        await db.commit()
        return True
    return False


async def create_mcp_scope_policy(
    db: AsyncSession,
    tenant_id: str,
    agent_id: uuid.UUID | None,
    mcp_server: str | None,
    rules: dict,
) -> AgentMCPScopePolicy:
    policy = AgentMCPScopePolicy(
        tenant_id=tenant_id,
        agent_id=agent_id,
        mcp_server=mcp_server,
        rules=rules,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy
