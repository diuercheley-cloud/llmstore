# Owner: agent-platform
from typing import Any


class MCPToolAdapter:
    def adapt(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("input_schema", {}),
            "mock": tool.get("mock", False),
        }
