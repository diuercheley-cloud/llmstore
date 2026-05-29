# Owner: agent-platform
from typing import Any

from .mcp_audit import MCPAuditLog
from .mcp_security import MCPSecurity


class MCPServer:
    def __init__(self):
        self.security = MCPSecurity()
        self.tools = {
            "safe_echo": lambda arguments: {"echo": self.security.sanitize_text(arguments.get("text", ""))},
            "readiness": lambda arguments: {"status": "ok", "surface": "agentic-platform"},
            "agent_run_status": lambda arguments: {"run_id": arguments.get("run_id"), "status": "unknown"},
        }
        self.resources = [{"uri": "mcp://status", "name": "status", "mime_type": "application/json"}]
        self.prompts = [{"name": "safe-summary", "description": "Summarize sanitized content"}]

    def list_tools(self) -> list[dict[str, Any]]:
        self.security.require_server_enabled()
        return [{"name": name, "description": f"Internal MCP tool: {name}"} for name in self.tools]

    def list_resources(self) -> list[dict[str, Any]]:
        self.security.require_server_enabled()
        return self.resources

    def list_prompts(self) -> list[dict[str, Any]]:
        self.security.require_server_enabled()
        return self.prompts

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.security.require_server_enabled()
        if tool_name not in self.tools:
            raise KeyError("MCP tool not found")
        result = self.tools[tool_name](arguments)
        MCPAuditLog.record("mcp_call", {"tool_name": tool_name}, tenant_id=None, server_id=None)
        return result
