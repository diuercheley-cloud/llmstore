# Owner: agent-platform
"""
MCP Prompt Adapter

Normalises raw prompt records from an MCP server.
"""

from __future__ import annotations

from typing import Any


class MCPPromptAdapter:
    def adapt(self, prompt: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": prompt.get("name"),
            "description": prompt.get("description", ""),
            "arguments": prompt.get("arguments", []),
            "mock": prompt.get("mock", False),
        }
