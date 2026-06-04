import pytest
from app.core.config import get_settings
from app.services.agents.mcp.mcp_audit import MCPAuditLog
from app.services.agents.mcp.mcp_client import MCPClient
from app.services.agents.mcp.mcp_registry import MCPRegistry
from app.services.agents.mcp.mcp_security import MCPSecurity
from app.services.agents.mcp.mcp_server import MCPServer


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

def test_mcp_client_discovers_mock_tools():
    settings = get_settings()
    settings.agent_mcp_enabled = True
    settings.agent_mcp_client_enabled = True
    settings.agent_mcp_external_network_enabled = True
    
    registry = MCPRegistry()
    server = registry.register("tenant-1", "my-server", "streamable_http", "http://local-mcp-server")
    
    client = MCPClient()
    discovered = client.discover(server.id)
    assert len(discovered["tools"]) > 0
    assert discovered["tools"][0]["name"] == "safe_echo"

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
    MCPAuditLog.events.clear()
    
    res = server.call("safe_echo", {"text": "hello"})
    assert res == {"echo": "hello"}
    assert len(MCPAuditLog.events) == 1
    assert MCPAuditLog.events[0]["event_type"] == "mcp_call"
