import os

os.environ["AGENT_MCP_ENABLED"] = "true"


import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.models.agents.agent_mcp_oauth import (
    AgentMCPDelegatedGrant,
    AgentMCPScopePolicy,
)
from app.services.agents.mcp.mcp_delegated_identity import resolve_mcp_identity
from app.services.agents.mcp.mcp_oauth import (
    MCPOAuthAuditLog,
    create_mcp_delegated_grant,
)
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_mcp_flags():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_oauth_token_exchange_enabled = True
    settings.agent_mcp_user_delegation_required = False
    settings.agent_mcp_global_credentials_allowed = True
    yield
    settings.agent_mcp_oauth_token_exchange_enabled = False
    settings.agent_mcp_user_delegation_required = False
    settings.agent_mcp_global_credentials_allowed = True


@pytest.mark.asyncio
async def test_delegation_required_no_grant_fails(session: AsyncSession):
    settings = get_settings()
    settings.agent_mcp_user_delegation_required = True

    # No grants are present. Identity resolution should raise PermissionError.
    with pytest.raises(
        PermissionError, match="Delegation required but no valid delegated grant found"
    ):
        await resolve_mcp_identity(
            db=session,
            tenant_id="tenant-A",
            user_id="user-1",
            agent_id=None,
            mcp_server="server-1",
        )


@pytest.mark.asyncio
async def test_scope_insufficient_fails(session: AsyncSession):
    # Create a grant with "read" scope
    grant = await create_mcp_delegated_grant(
        db=session,
        tenant_id="tenant-A",
        user_id="user-1",
        agent_id=None,
        mcp_server="server-1",
        access_token="tok-123",
        refresh_token=None,
        scopes=["read"],
        expires_at=None,
    )

    # Configure a scope policy that requires "write" scope for tool "edit"
    policy = AgentMCPScopePolicy(
        tenant_id="tenant-A",
        agent_id=None,
        mcp_server="server-1",
        rules={"tool_policies": {"edit": {"required_scopes": ["write"]}}},
    )
    session.add(policy)
    await session.commit()

    # Checking tool "edit" (requires "write", but grant only has "read")
    with pytest.raises(PermissionError, match="Insufficient scope"):
        await resolve_mcp_identity(
            db=session,
            tenant_id="tenant-A",
            user_id="user-1",
            agent_id=None,
            mcp_server="server-1",
            tool="edit",
        )


@pytest.mark.asyncio
async def test_grant_revoked_fails(session: AsyncSession):
    # Create a revoked grant
    grant = AgentMCPDelegatedGrant(
        tenant_id="tenant-A",
        user_id="user-1",
        agent_id=None,
        mcp_server="server-1",
        access_token="tok-123",
        refresh_token=None,
        scopes=["*"],
        expires_at=None,
        is_revoked=True,
    )
    session.add(grant)
    await session.commit()

    # Enforce delegation requirement so it doesn't fall back to global
    settings = get_settings()
    settings.agent_mcp_user_delegation_required = True

    # Identity resolution should fail because grant is revoked
    with pytest.raises(PermissionError, match="no valid delegated grant found"):
        await resolve_mcp_identity(
            db=session,
            tenant_id="tenant-A",
            user_id="user-1",
            agent_id=None,
            mcp_server="server-1",
        )


@pytest.mark.asyncio
async def test_token_not_in_logs_or_responses(
    session: AsyncSession, admin_client: AsyncClient, admin_token_headers
):
    # Test API responses do not leak raw token
    grant_payload = {
        "tenant_id": "tenant-A",
        "user_id": "user-1",
        "mcp_server": "server-1",
        "access_token": "my-secret-access-token",
        "refresh_token": "my-secret-refresh-token",
        "scopes": ["*"],
    }

    resp = await admin_client.post(
        "/admin/agents/mcp/oauth/grants",
        headers=admin_token_headers,
        json=grant_payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "[REDACTED]"
    assert data["refresh_token"] == "[REDACTED]"

    # Test audit logs do not leak token
    MCPOAuthAuditLog.events.clear()
    await resolve_mcp_identity(
        db=session,
        tenant_id="tenant-A",
        user_id="user-1",
        agent_id=None,
        mcp_server="server-1",
    )
    assert len(MCPOAuthAuditLog.events) > 0
    event = MCPOAuthAuditLog.events[-1]

    # Raw token strings should not be in the audit log values
    event_str = str(event)
    assert "my-secret-access-token" not in event_str
    assert "my-secret-refresh-token" not in event_str


@pytest.mark.asyncio
async def test_global_fallback_blocked_when_flag_false(session: AsyncSession):
    settings = get_settings()
    settings.agent_mcp_global_credentials_allowed = False

    # Resolution should fail when no grant and fallback is false
    with pytest.raises(PermissionError, match="no valid delegated grant found"):
        await resolve_mcp_identity(
            db=session,
            tenant_id="tenant-A",
            user_id="user-1",
            agent_id=None,
            mcp_server="server-1",
        )


@pytest.mark.asyncio
async def test_tenant_isolation_mismatch(session: AsyncSession):
    # Create grant for tenant-A
    await create_mcp_delegated_grant(
        db=session,
        tenant_id="tenant-A",
        user_id="user-1",
        agent_id=None,
        mcp_server="server-1",
        access_token="tok-123",
        refresh_token=None,
        scopes=["*"],
        expires_at=None,
    )

    # Try resolving identity for tenant-B.
    # It should fall back to global because it cannot see tenant-A's grant.
    res = await resolve_mcp_identity(
        db=session,
        tenant_id="tenant-B",
        user_id="user-1",
        agent_id=None,
        mcp_server="server-1",
    )
    assert res["resolved_type"] == "global_fallback"
