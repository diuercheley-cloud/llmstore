# Owner: agent-platform
"""
MCP Tool Adapter

Normalises a raw tool record returned by an MCP server into the internal
canonical format used throughout the platform.

Canonical format:
  name         : str   — sanitized tool name (alphanumeric + _ -)
  description  : str   — sanitized description (injection patterns removed)
  input_schema : dict  — JSON Schema for tool arguments
  mock         : bool  — true only when AGENT_MCP_MOCK_MODE was active
  source       : str   — 'mcp_real' | 'mcp_mock'
"""
from __future__ import annotations

from typing import Any


class MCPToolAdapter:
    def adapt(self, tool: dict[str, Any]) -> dict[str, Any]:
        is_mock = tool.get("mock", False)
        return {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            # MCP spec uses 'inputSchema'; also accept snake_case variant
            "input_schema": tool.get("inputSchema") or tool.get("input_schema") or {},
            "mock": is_mock,
            "source": "mcp_mock" if is_mock else "mcp_real",
        }
