# Owner: agent-platform
import uuid
from datetime import timedelta

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_mcp_oauth import (
    AgentMCPDelegatedGrant,
    AgentMCPScopePolicy,
)
from app.services.agents.mcp.mcp_oauth import MCPOAuthAuditLog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_scope_policy(
    db: AsyncSession,
    tenant_id: str,
    agent_id: uuid.UUID | None,
    mcp_server: str,
    tool: str | None,
    action: str | None,
    grant_scopes: list[str],
) -> None:
    result = await db.execute(
        select(AgentMCPScopePolicy).where(
            AgentMCPScopePolicy.tenant_id == tenant_id,
            (AgentMCPScopePolicy.mcp_server == mcp_server) | (AgentMCPScopePolicy.mcp_server == None)
        )
    )
    policies = result.scalars().all()
    for policy in policies:
        rules = policy.rules or {}

        # 1. Allowed tools check
        allowed_tools = rules.get("allowed_tools")
        if allowed_tools is not None:
            if tool not in allowed_tools and "*" not in allowed_tools:
                raise PermissionError(f"Tool {tool} not allowed by policy")

        # 2. Blocked tools check
        blocked_tools = rules.get("blocked_tools", [])
        if tool in blocked_tools:
            raise PermissionError(f"Tool {tool} is blocked by policy")

        # 3. Required scopes check
        required_scopes = list(rules.get("required_scopes", []))
        if tool:
            tool_policy = rules.get("tool_policies", {}).get(tool, {})
            required_scopes.extend(tool_policy.get("required_scopes", []))

        for req_scope in required_scopes:
            if req_scope not in grant_scopes and "*" not in grant_scopes:
                raise PermissionError(f"Insufficient scope: requires {req_scope}")


async def resolve_mcp_identity(
    db: AsyncSession,
    tenant_id: str,
    user_id: str | None,
    agent_id: uuid.UUID | None,
    mcp_server: str,
    tool: str | None = None,
    action: str | None = None,
) -> dict:
    settings = get_settings()

    # 1. Feature Flag Check
    if not settings.agent_mcp_oauth_token_exchange_enabled:
        if settings.agent_mcp_user_delegation_required:
            MCPOAuthAuditLog.record(
                grant_id=None,
                scopes=[],
                user_id=user_id,
                tenant_id=tenant_id,
                mcp_server=mcp_server,
                tool=tool,
                policy_decision="deny: delegation_required_but_oauth_disabled",
            )
            raise PermissionError("User delegation required but OAuth/Token Exchange is disabled")

        if settings.agent_mcp_global_credentials_allowed:
            MCPOAuthAuditLog.record(
                grant_id=None,
                scopes=[],
                user_id=user_id,
                tenant_id=tenant_id,
                mcp_server=mcp_server,
                tool=tool,
                policy_decision="allow: global_fallback_oauth_disabled",
            )
            return {"resolved_type": "global_fallback", "token": "global-stack-token"}

        MCPOAuthAuditLog.record(
            grant_id=None,
            scopes=[],
            user_id=user_id,
            tenant_id=tenant_id,
            mcp_server=mcp_server,
            tool=tool,
            policy_decision="deny: oauth_disabled_and_global_fallback_blocked",
        )
        raise PermissionError("OAuth/Token Exchange is disabled and global fallback is not allowed")

    # 2. Resolve User Delegated Grant
    grant = None
    if user_id:
        result = await db.execute(
            select(AgentMCPDelegatedGrant).where(
                AgentMCPDelegatedGrant.tenant_id == tenant_id,
                AgentMCPDelegatedGrant.user_id == user_id,
                AgentMCPDelegatedGrant.mcp_server == mcp_server,
                AgentMCPDelegatedGrant.is_revoked == False,
            )
        )
        grant = result.scalar_one_or_none()

    # 3. Fallback to Tenant Service Principal Grant
    if not grant:
        # Search for a service principal grant for the tenant
        result = await db.execute(
            select(AgentMCPDelegatedGrant).where(
                AgentMCPDelegatedGrant.tenant_id == tenant_id,
                AgentMCPDelegatedGrant.user_id == "service_principal",
                AgentMCPDelegatedGrant.mcp_server == mcp_server,
                AgentMCPDelegatedGrant.is_revoked == False,
            )
        )
        grant = result.scalar_one_or_none()

    # 4. Handle Case When Grant Exists
    if grant:
        # Check Expiration
        if grant.expires_at and grant.expires_at < utc_now():
            if grant.refresh_token:
                # Extend validity (Simulated renewal)
                grant.expires_at = utc_now() + timedelta(seconds=3600)
                grant.access_token = f"refreshed_tok_{uuid.uuid4()}"
                await db.commit()
            else:
                MCPOAuthAuditLog.record(
                    grant_id=grant.id,
                    scopes=grant.scopes,
                    user_id=grant.user_id,
                    tenant_id=tenant_id,
                    mcp_server=mcp_server,
                    tool=tool,
                    policy_decision="deny: token_expired",
                )
                raise PermissionError("Token expired")

        # Check Scope Policy
        try:
            await check_scope_policy(db, tenant_id, agent_id, mcp_server, tool, action, grant.scopes)
        except PermissionError as exc:
            MCPOAuthAuditLog.record(
                grant_id=grant.id,
                scopes=grant.scopes,
                user_id=grant.user_id,
                tenant_id=tenant_id,
                mcp_server=mcp_server,
                tool=tool,
                policy_decision=f"deny: {str(exc)}",
            )
            raise exc

        MCPOAuthAuditLog.record(
            grant_id=grant.id,
            scopes=grant.scopes,
            user_id=grant.user_id,
            tenant_id=tenant_id,
            mcp_server=mcp_server,
            tool=tool,
            policy_decision="allow",
        )
        resolved_type = "user_delegated" if grant.user_id != "service_principal" else "tenant_service_principal"
        return {
            "resolved_type": resolved_type,
            "token": grant.access_token,
            "grant_id": grant.id,
            "scopes": grant.scopes,
        }

    # 5. Global Fallback if no grant found
    if settings.agent_mcp_global_credentials_allowed and not settings.agent_mcp_user_delegation_required:
        MCPOAuthAuditLog.record(
            grant_id=None,
            scopes=[],
            user_id=user_id,
            tenant_id=tenant_id,
            mcp_server=mcp_server,
            tool=tool,
            policy_decision="allow: global_fallback_no_grant",
        )
        return {"resolved_type": "global_fallback", "token": "global-stack-token"}

    MCPOAuthAuditLog.record(
        grant_id=None,
        scopes=[],
        user_id=user_id,
        tenant_id=tenant_id,
        mcp_server=mcp_server,
        tool=tool,
        policy_decision="deny: delegation_required_no_grant",
    )
    raise PermissionError("Delegation required but no valid delegated grant found")
