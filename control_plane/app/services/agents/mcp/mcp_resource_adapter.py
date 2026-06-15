# Owner: agent-platform
"""
MCP Resource Adapter

Normalises raw resource records from an MCP server into the internal
canonical format.
"""

from __future__ import annotations

from typing import Any


class MCPResourceAdapter:
    def adapt(self, resource: dict[str, Any]) -> dict[str, Any]:
        return {
            "uri": resource.get("uri"),
            "name": resource.get("name"),
            # MCP spec uses mimeType (camelCase); also accept snake_case
            "mime_type": resource.get("mimeType") or resource.get("mime_type", "text/plain"),
            "mock": resource.get("mock", False),
        }
