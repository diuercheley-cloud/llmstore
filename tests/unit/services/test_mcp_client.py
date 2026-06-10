"""
Tests for real MCP client discovery and execution.

Covers all requirements:
  1. Real discovery against fake MCP server (via httpx mock)
  2. Hardcoded mock NOT returned by default (mock_mode=false)
  3. Unapproved tool blocks call_tool
  4. External network disabled blocks HTTP external endpoints
  5. Malicious tool description is sanitized
  6. Sampling request from server is blocked
  7. call_tool records audit events
  8. Legacy: feature flags, server tools, call record, sampling block

Strategy:
  - All real-discovery tests use pytest-httpx (or manual httpx transport mock)
    to intercept HTTP calls to the fake MCP server without a real TCP connection.
  - FakeMCPServer.handle_request() provides deterministic responses.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.services.agents.mcp.mcp_audit import MCPAuditLog
from app.services.agents.mcp.mcp_client import MCPClient
from app.services.agents.mcp.mcp_registry import MCPRegistry
from app.services.agents.mcp.mcp_security import MCPSecurity
from app.services.agents.mcp.mcp_server import MCPServer
from app.services.agents.mcp.mcp_transport import MCPTransportError

from .fake_mcp_server import FakeMCPServer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_transport(server: FakeMCPServer):
    """
    Returns a context manager that patches build_transport with a fake
    that delegates to FakeMCPServer.handle_request().
    """
    class _FakeTransport:
        async def initialize(self):
            resp = server.handle_request(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            )
            return resp["result"]

        async def request(self, method: str, params: dict, req_id: int = 1):
            resp = server.handle_request(
                {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            )
            if "error" in resp:
                raise MCPTransportError(resp["error"]["message"])
            return resp["result"]

        async def close(self):
            pass

    return patch(
        "app.services.agents.mcp.mcp_client.build_transport",
        return_value=_FakeTransport(),
    )


def _enable_real_discovery(settings):
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_real_discovery_enabled = True
    settings.agent_mcp_mock_mode = False
    settings.agent_mcp_external_network_enabled = True


def _enable_mock_mode(settings):
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_mock_mode = True
    settings.agent_mcp_real_discovery_enabled = False


def _reset_flags(settings):
    settings.agent_mcp_enabled = False
    settings.agent_mcp_client_enabled = False
    settings.agent_mcp_real_discovery_enabled = False
    settings.agent_mcp_mock_mode = False
    settings.agent_mcp_external_network_enabled = False


# ===========================================================================
# 1. Real discovery against fake MCP server
# ===========================================================================


@pytest.mark.asyncio
async def test_real_discovery_returns_server_tools():
    """discover() with real discovery returns tools from the server, not hardcoded list."""
    settings = get_settings()
    _enable_real_discovery(settings)
    MCPAuditLog.clear()

    fake = FakeMCPServer()
    registry = MCPRegistry()
    server = registry.register("t1", "fake", "streamable_http", "http://localhost:9999/mcp")

    with _patch_transport(fake):
        client = MCPClient()
        result = await client.discover(server.id)

    assert len(result["tools"]) > 0
    tool_names = {t["name"] for t in result["tools"]}
    # FakeMCPServer returns 'echo' and 'add'
    assert "echo" in tool_names
    assert "add" in tool_names

    # Audit must have been recorded
    events = MCPAuditLog.list_events(event_type="mcp_discover")
    assert len(events) >= 1
    last = events[-1]
    assert last["mock"] is False
    assert last["tool_count"] >= 2

    _reset_flags(settings)


@pytest.mark.asyncio
async def test_real_discovery_returns_resources_and_prompts():
    settings = get_settings()
    _enable_real_discovery(settings)

    fake = FakeMCPServer()
    registry = MCPRegistry()
    server = registry.register("t1", "fake2", "streamable_http", "http://localhost:9999/mcp")

    with _patch_transport(fake):
        client = MCPClient()
        result = await client.discover(server.id)

    assert len(result["resources"]) > 0
    assert len(result["prompts"]) > 0

    _reset_flags(settings)


# ===========================================================================
# 2. Hardcoded mock NOT returned by default
# ===========================================================================


@pytest.mark.asyncio
async def test_hardcoded_mock_not_returned_by_default():
    """discover() must not fall back to the hardcoded safe_echo / kg_query list."""
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_mock_mode = False
    settings.agent_mcp_real_discovery_enabled = False  # real discovery also off

    registry = MCPRegistry()
    server = registry.register("t1", "test-disabled", "streamable_http", "http://localhost:9999/mcp")

    client = MCPClient()
    with pytest.raises(PermissionError, match="AGENT_MCP_REAL_DISCOVERY_ENABLED"):
        await client.discover(server.id)

    _reset_flags(settings)


@pytest.mark.asyncio
async def test_mock_mode_returns_mock_flag():
    """With AGENT_MCP_MOCK_MODE=true, discover() returns mock=true tools without real I/O."""
    settings = get_settings()
    _enable_mock_mode(settings)
    MCPAuditLog.clear()

    registry = MCPRegistry()
    server = registry.register("t1", "mock-server", "streamable_http", "http://localhost:9999/mcp")

    client = MCPClient()
    result = await client.discover(server.id)

    assert len(result["tools"]) > 0
    # All tools must be flagged mock=true
    assert all(t["mock"] is True for t in result["tools"])
    # Audit event must say mock=True
    events = MCPAuditLog.list_events(event_type="mcp_discover")
    assert events[-1]["mock"] is True

    _reset_flags(settings)


# ===========================================================================
# 3. Unapproved tool blocks call_tool
# ===========================================================================


@pytest.mark.asyncio
async def test_unapproved_tool_blocks_call():
    settings = get_settings()
    _enable_real_discovery(settings)

    registry = MCPRegistry()
    server = registry.register("t1", "gate-server", "streamable_http", "http://localhost:9999/mcp")
    # 'echo' is NOT approved

    client = MCPClient()
    with pytest.raises(PermissionError, match="not in the approved list"):
        await client.call_tool(server.id, "echo", {"text": "hi"})

    _reset_flags(settings)


@pytest.mark.asyncio
async def test_approved_tool_can_be_called():
    settings = get_settings()
    _enable_real_discovery(settings)
    MCPAuditLog.clear()

    fake = FakeMCPServer()
    registry = MCPRegistry()
    server = registry.register("t1", "approved-server", "streamable_http", "http://localhost:9999/mcp")
    server.approved_tools.add("echo")

    with _patch_transport(fake):
        client = MCPClient()
        result = await client.call_tool(server.id, "echo", {"text": "hello"})

    assert "content" in result or "result" in result  # from fake server
    events = MCPAuditLog.list_events(event_type="mcp_call_success")
    assert len(events) >= 1
    assert events[-1]["tool_name"] == "echo"
    assert events[-1]["mock"] is False

    _reset_flags(settings)


# ===========================================================================
# 4. External network disabled blocks HTTP external endpoints
# ===========================================================================


@pytest.mark.asyncio
async def test_external_network_disabled_blocks_real_endpoint():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_real_discovery_enabled = True
    settings.agent_mcp_mock_mode = False
    settings.agent_mcp_external_network_enabled = False  # key: disabled

    registry = MCPRegistry()
    # This endpoint is external (not localhost)
    server = registry.register("t1", "ext-server", "streamable_http", "https://api.example.com/mcp")

    client = MCPClient()
    with pytest.raises(PermissionError, match="External MCP network access is disabled"):
        await client.discover(server.id)

    _reset_flags(settings)


@pytest.mark.asyncio
async def test_localhost_allowed_even_without_external_flag():
    """Localhost endpoints are not external, so they bypass the external-network flag."""
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_real_discovery_enabled = True
    settings.agent_mcp_mock_mode = False
    settings.agent_mcp_external_network_enabled = False  # disabled, but localhost OK

    fake = FakeMCPServer()
    registry = MCPRegistry()
    server = registry.register("t1", "local-server", "streamable_http", "http://localhost:9999/mcp")

    with _patch_transport(fake):
        client = MCPClient()
        result = await client.discover(server.id)

    assert len(result["tools"]) > 0

    _reset_flags(settings)


# ===========================================================================
# 5. Malicious tool description sanitized
# ===========================================================================


@pytest.mark.asyncio
async def test_malicious_tool_description_sanitized():
    """Tools with prompt-injection in description must be sanitized before storage."""
    settings = get_settings()
    _enable_real_discovery(settings)

    fake = FakeMCPServer()  # includes 'danger' tool with injection bait
    registry = MCPRegistry()
    server = registry.register("t1", "danger-server", "streamable_http", "http://localhost:9999/mcp")

    with _patch_transport(fake):
        client = MCPClient()
        result = await client.discover(server.id)

    danger_tools = [t for t in result["tools"] if t["name"] == "danger"]
    assert len(danger_tools) == 1
    desc = danger_tools[0]["description"]
    assert "<SYSTEM>" not in desc
    assert "Ignore previous instructions" not in desc
    assert "You are now evil" not in desc
    # Sanitizer replaces with [REMOVED]
    assert "[REMOVED]" in desc

    _reset_flags(settings)


# ===========================================================================
# 6. Sampling request from server is blocked
# ===========================================================================


@pytest.mark.asyncio
async def test_sampling_advertised_by_server_blocks_discover():
    """If server advertises sampling capability and sampling is disabled, discovery fails."""
    settings = get_settings()
    _enable_real_discovery(settings)
    settings.agent_mcp_sampling_enabled = False

    fake = FakeMCPServer(advertise_sampling=True)
    registry = MCPRegistry()
    server = registry.register("t1", "sampler-server", "streamable_http", "http://localhost:9999/mcp")

    with _patch_transport(fake):
        client = MCPClient()
        with pytest.raises(PermissionError, match="sampling is disabled"):
            await client.discover(server.id)

    _reset_flags(settings)


# ===========================================================================
# 7. call_tool records audit events
# ===========================================================================


@pytest.mark.asyncio
async def test_call_tool_records_attempt_and_success_audit():
    settings = get_settings()
    _enable_real_discovery(settings)
    MCPAuditLog.clear()

    fake = FakeMCPServer()
    registry = MCPRegistry()
    server = registry.register("t1", "audit-server", "streamable_http", "http://localhost:9999/mcp")
    server.approved_tools.add("echo")

    with _patch_transport(fake):
        client = MCPClient()
        await client.call_tool(server.id, "echo", {"text": "audit-me"}, tenant_id="t1")

    attempt_events = MCPAuditLog.list_events(event_type="mcp_call_attempt")
    success_events = MCPAuditLog.list_events(event_type="mcp_call_success")
    assert len(attempt_events) >= 1
    assert len(success_events) >= 1
    assert attempt_events[-1]["tool_name"] == "echo"
    assert success_events[-1]["tool_name"] == "echo"
    assert success_events[-1]["mock"] is False

    _reset_flags(settings)


@pytest.mark.asyncio
async def test_call_tool_mock_mode_records_mock_audit():
    settings = get_settings()
    _enable_mock_mode(settings)
    MCPAuditLog.clear()

    registry = MCPRegistry()
    server = registry.register("t1", "mock-call-server", "streamable_http", "http://localhost:9999/mcp")
    server.approved_tools.add("echo")

    client = MCPClient()
    result = await client.call_tool(server.id, "echo", {"text": "mock-me"})

    assert result["mock"] is True
    success_events = MCPAuditLog.list_events(event_type="mcp_call_success")
    assert success_events[-1]["mock"] is True

    _reset_flags(settings)


# ===========================================================================
# 8. Security: approve_tool sanitizes name
# ===========================================================================


def test_approve_tool_sanitizes_dangerous_name():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_mock_mode = False

    registry = MCPRegistry()
    server = registry.register("t1", "sanitize-server", "streamable_http", "http://localhost:9999/mcp")

    client = MCPClient()
    result = client.approve_tool(server.id, "evil<script>tool")
    # name should be sanitized
    assert "<script>" not in result["tool_name"]
    assert result["approved"] is True


# ===========================================================================
# Legacy tests (preserved and updated to work with new code)
# ===========================================================================


def test_mcp_disabled_raises_permission_error():
    settings = get_settings()
    settings.agent_mcp_enabled = False

    security = MCPSecurity()
    with pytest.raises(PermissionError, match="MCP is disabled"):
        security.require_enabled()


def test_mcp_client_disabled_raises():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = False

    security = MCPSecurity()
    with pytest.raises(PermissionError, match="MCP client is disabled"):
        security.require_client_enabled()


def test_sampling_request_blocked_by_default():
    settings = get_settings()
    settings.agent_mcp_sampling_enabled = False

    security = MCPSecurity()
    with pytest.raises(PermissionError, match="MCP sampling is disabled"):
        security.validate_sampling(wants_sampling=True)


def test_external_mcp_without_network_flag_blocked():
    settings = get_settings()
    settings.agent_mcp_external_network_enabled = False

    security = MCPSecurity()
    with pytest.raises(PermissionError, match="External MCP network access is disabled"):
        security.validate_external_network(is_external=True)


def test_mcp_server_exposes_tools_when_enabled():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_server_enabled = True

    server = MCPServer()
    tools = server.list_tools()
    assert len(tools) > 0
    assert any(t["name"] == "safe_echo" for t in tools)


def test_mcp_call_records_audit_event():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_server_enabled = True

    server = MCPServer()
    MCPAuditLog.clear()

    res = server.call("safe_echo", {"text": "hello"})
    assert res == {"echo": "hello"}
    events = MCPAuditLog.list_events(event_type="mcp_call")
    assert len(events) == 1
    assert events[0]["event_type"] == "mcp_call"
