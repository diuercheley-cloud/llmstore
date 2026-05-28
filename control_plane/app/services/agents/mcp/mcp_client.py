# Owner: agent-platform
from typing import Any

from .mcp_audit import MCPAuditLog
from .mcp_prompt_adapter import MCPPromptAdapter
from .mcp_registry import MCPRegistry
from .mcp_resource_adapter import MCPResourceAdapter
from .mcp_security import MCPSecurity
from .mcp_tool_adapter import MCPToolAdapter


class MCPClient:
    def __init__(self):
        self.registry = MCPRegistry()
        self.security = MCPSecurity()
        self.tool_adapter = MCPToolAdapter()
        self.resource_adapter = MCPResourceAdapter()
        self.prompt_adapter = MCPPromptAdapter()

    def discover(self, server_id: str) -> dict[str, Any]:
        self.security.require_client_enabled()
        server = self.registry.get(server_id)
        if not server:
            raise KeyError("MCP server not found")
        self.security.validate_external_network(server.endpoint.startswith("http"))
        discovered = {
            "tools": [
                self.tool_adapter.adapt({"name": "safe_echo", "description": "Returns sanitized text", "mock": True}),
                self.tool_adapter.adapt({"name": "kg_query", "description": "Runs a tenant-scoped KG query", "mock": True}),
            ],
            "resources": [
                self.resource_adapter.adapt({"uri": "mcp://status", "name": "status"}),
            ],
            "prompts": [
                self.prompt_adapter.adapt({"name": "safe-summary", "description": "Summarize without secrets"}),
            ],
        }
        server.discovered_tools = discovered["tools"]
        server.discovered_resources = discovered["resources"]
        server.discovered_prompts = discovered["prompts"]
        MCPAuditLog.record("mcp_discover", {"server_id": server_id, "tools": [tool["name"] for tool in discovered["tools"]]})
        return discovered

    def approve_tool(self, server_id: str, tool_name: str) -> dict[str, Any]:
        server = self.registry.get(server_id)
        if not server:
            raise KeyError("MCP server not found")
        server.approved_tools.add(tool_name)
        return {"server_id": server_id, "tool_name": tool_name, "approved": True}
