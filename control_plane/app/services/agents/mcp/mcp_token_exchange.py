# Owner: agent-platform
import hashlib
import uuid
from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.agents.agent_mcp_oauth import (
    AgentMCPDelegatedGrant,
    AgentMCPScopePolicy,
    AgentMCPTokenExchange,
)
from app.services.agents.mcp.mcp_oauth import MCPOAuthAuditLog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def exchange_token(
    db: AsyncSession,
    tenant_id: str,
    subject_token: str,
    subject_token_type: str,
    mcp_server: str,
    requested_scopes: list[str],
) -> dict[str, Any]:
    # Search by access_token matching subject_token
    result = await db.execute(
        select(AgentMCPDelegatedGrant).where(
            AgentMCPDelegatedGrant.access_token == subject_token,
            AgentMCPDelegatedGrant.tenant_id == tenant_id,
        )
    )
    grant = result.scalar_one_or_none()

    if not grant:
        MCPOAuthAuditLog.record(
            grant_id=None,
            scopes=requested_scopes,
            user_id=None,
            tenant_id=tenant_id,
            mcp_server=mcp_server,
            tool=None,
            policy_decision="deny: no_grant_found",
        )
        raise HTTPException(status_code=400, detail="Invalid subject token / grant not found")

    if grant.is_revoked:
        MCPOAuthAuditLog.record(
            grant_id=grant.id,
            scopes=requested_scopes,
            user_id=grant.user_id,
            tenant_id=tenant_id,
            mcp_server=mcp_server,
            tool=None,
            policy_decision="deny: grant_revoked",
        )
        raise HTTPException(status_code=400, detail="Grant is revoked")

    # Check expiration
    if grant.expires_at and grant.expires_at < utc_now():
        if grant.refresh_token:
            # Perform simulated token refresh
            grant.expires_at = utc_now() + timedelta(seconds=3600)
            grant.access_token = f"refreshed_tok_{uuid.uuid4()}"
            await db.commit()
        else:
            MCPOAuthAuditLog.record(
                grant_id=grant.id,
                scopes=requested_scopes,
                user_id=grant.user_id,
                tenant_id=tenant_id,
                mcp_server=mcp_server,
                tool=None,
                policy_decision="deny: grant_expired",
            )
            raise HTTPException(status_code=400, detail="Token expired")

    # Fetch scope policies
    policy_result = await db.execute(
        select(AgentMCPScopePolicy).where(
            AgentMCPScopePolicy.tenant_id == tenant_id,
            (AgentMCPScopePolicy.mcp_server == mcp_server)
            | (AgentMCPScopePolicy.mcp_server == None),
        )
    )
    policies = policy_result.scalars().all()

    # Rule checks from policies
    for policy in policies:
        rules = policy.rules or {}
        # If rules block specific requested scopes, tools or actions
        blocked_scopes = rules.get("blocked_scopes", [])
        for bs in blocked_scopes:
            if bs in requested_scopes:
                MCPOAuthAuditLog.record(
                    grant_id=grant.id,
                    scopes=requested_scopes,
                    user_id=grant.user_id,
                    tenant_id=tenant_id,
                    mcp_server=mcp_server,
                    tool=None,
                    policy_decision="deny: scope_blocked_by_policy",
                )
                raise HTTPException(status_code=403, detail=f"Scope {bs} blocked by policy")

    # Verify grant scopes are sufficient
    for scope in requested_scopes:
        if scope not in grant.scopes and "*" not in grant.scopes:
            MCPOAuthAuditLog.record(
                grant_id=grant.id,
                scopes=requested_scopes,
                user_id=grant.user_id,
                tenant_id=tenant_id,
                mcp_server=mcp_server,
                tool=None,
                policy_decision="deny: scope_insufficient",
            )
            raise HTTPException(status_code=403, detail=f"Insufficient scope: {scope}")

    # Generate new exchanged token
    exchanged_token = f"mcp_ex_{uuid.uuid4()}"
    exchanged_token_hash = hashlib.sha256(exchanged_token.encode()).hexdigest()
    subject_token_hash = hashlib.sha256(subject_token.encode()).hexdigest()

    expires_in = 3600
    expires_at = utc_now() + timedelta(seconds=expires_in)

    token_exchange = AgentMCPTokenExchange(
        tenant_id=tenant_id,
        user_id=grant.user_id,
        agent_id=grant.agent_id,
        grant_id=grant.id,
        mcp_server=mcp_server,
        subject_token_hash=subject_token_hash,
        exchanged_token_hash=exchanged_token_hash,
        scopes=requested_scopes,
        expires_at=expires_at,
    )
    db.add(token_exchange)
    await db.commit()

    MCPOAuthAuditLog.record(
        grant_id=grant.id,
        scopes=requested_scopes,
        user_id=grant.user_id,
        tenant_id=tenant_id,
        mcp_server=mcp_server,
        tool=None,
        policy_decision="allow",
    )

    return {
        "access_token": exchanged_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "scope": " ".join(requested_scopes) if requested_scopes else "",
    }
