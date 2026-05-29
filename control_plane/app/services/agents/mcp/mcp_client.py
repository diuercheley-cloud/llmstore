# Owner: agent-platform
"""
MCP Client — Real Discovery and Execution

Replaces the hardcoded mock-tool list with genuine MCP protocol communication.

Discovery flow:
  1. validate security gates (client_enabled, external_network, etc.)
  2. lookup server from registry
  3. build transport (HTTP or stdio) for the server's config
  4. send MCP 'initialize' handshake
  5. call 'tools/list', 'resources/list', 'prompts/list'
  6. sanitize every tool name/description
  7. store results on the server record
  8. audit each event

Execution flow:
  1. validate security gates
  2. validate tool is in approved_tools set
  3. call 'tools/call' via transport
  4. audit call with result status

Mock mode:
  - ONLY active when AGENT_MCP_MOCK_MODE=true
  - Returned tool records carry mock=true so callers can detect it
  - Real discovery is NEVER triggered in mock mode

Feature flags:
  AGENT_MCP_CLIENT_ENABLED          (required)
  AGENT_MCP_REAL_DISCOVERY_ENABLED  (required for discover())
  AGENT_MCP_MOCK_MODE               (test/staging only)
  AGENT_MCP_EXTERNAL_NETWORK_ENABLED (required for non-localhost HTTP)
  AGENT_MCP_CALL_TIMEOUT_MS
  AGENT_MCP_CALL_MAX_RETRIES
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.core.config import get_settings

from .mcp_audit import MCPAuditLog
from .mcp_prompt_adapter import MCPPromptAdapter
from .mcp_registry import MCPRegistry, MCPServerRecord
from .mcp_resource_adapter import MCPResourceAdapter
from .mcp_security import MCPSecurity
from .mcp_tool_adapter import MCPToolAdapter
from .mcp_transport import MCPTransportError, build_transport

logger = logging.getLogger(__name__)

_MOCK_TOOLS: list[dict[str, Any]] = [
    {
        "name": "safe_echo",
        "description": "Returns sanitized text (mock)",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
        "mock": True,
    },
    {
        "name": "kg_query",
        "description": "Runs a tenant-scoped KG query (mock)",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        "mock": True,
    },
]
_MOCK_RESOURCES: list[dict[str, Any]] = [
    {"uri": "mcp://status", "name": "status", "mock": True},
]
_MOCK_PROMPTS: list[dict[str, Any]] = [
    {"name": "safe-summary", "description": "Summarize without secrets (mock)", "mock": True},
]


class MCPClient:
    def __init__(self):
        self.registry = MCPRegistry()
        self.security = MCPSecurity()
        self.tool_adapter = MCPToolAdapter()
        self.resource_adapter = MCPResourceAdapter()
        self.prompt_adapter = MCPPromptAdapter()
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, server_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        """
        Discover tools/resources/prompts from an MCP server.

        Decision matrix:
          AGENT_MCP_MOCK_MODE=true          → return mock catalogue (no real I/O)
          AGENT_MCP_REAL_DISCOVERY_ENABLED  → real MCP initialize + list calls
          neither                           → raise PermissionError

        An empty tool list is NEVER returned silently: if discovery fails,
        the exception propagates so callers know why.
        """
        self.security.require_client_enabled()
        server = self._get_server(server_id, tenant_id)

        # ---- Mock mode (test/staging only) ----
        if self.security.is_mock_mode():
            return self._mock_discover(server)

        # ---- Real discovery ----
        self.security.require_real_discovery()
        is_external = self.security.is_external_endpoint(server.endpoint)
        self.security.validate_external_network(is_external)

        started = time.monotonic()
        transport = build_transport(
            server.transport,
            server.endpoint,
            self._settings.agent_mcp_call_timeout_ms,
        )
        try:
            return await self._real_discover(server, transport, started)
        finally:
            await transport.close()

    async def _real_discover(
        self,
        server: MCPServerRecord,
        transport: Any,
        started: float,
    ) -> dict[str, Any]:
        """Perform initialize + list calls with retry logic."""
        max_retries = self._settings.agent_mcp_call_max_retries

        async def _call_with_retry(method: str, params: dict) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await transport.request(method, params, req_id=attempt + 1)
                except MCPTransportError as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
            raise last_exc  # type: ignore[misc]

        # MCP initialize handshake
        init_result = await transport.initialize()
        server_info = init_result.get("serverInfo", {})
        server_caps = init_result.get("capabilities", {})

        # Block sampling if server advertises it and we don't allow it.
        # MCP spec: sampling capability is signalled by the KEY being present
        # in the capabilities dict (value may be {}, which bool({}) == False).
        self.security.validate_sampling("sampling" in server_caps)

        # tools/list
        tools_raw = await _call_with_retry("tools/list", {})
        raw_tools: list[dict] = tools_raw.get("tools", []) if isinstance(tools_raw, dict) else []

        # resources/list
        resources_raw = await _call_with_retry("resources/list", {})
        raw_resources: list[dict] = (
            resources_raw.get("resources", []) if isinstance(resources_raw, dict) else []
        )

        # prompts/list
        prompts_raw = await _call_with_retry("prompts/list", {})
        raw_prompts: list[dict] = (
            prompts_raw.get("prompts", []) if isinstance(prompts_raw, dict) else []
        )

        # Validate + sanitize each tool
        tools: list[dict] = []
        for raw in raw_tools:
            self.security.validate_tool_schema(raw)
            sanitized = self.security.sanitize_tool(raw)
            tools.append(self.tool_adapter.adapt(sanitized))

        resources = [self.resource_adapter.adapt(r) for r in raw_resources]
        prompts = [self.prompt_adapter.adapt(p) for p in raw_prompts]

        server.discovered_tools = tools
        server.discovered_resources = resources
        server.discovered_prompts = prompts
        server.server_info = server_info

        elapsed_ms = (time.monotonic() - started) * 1000
        MCPAuditLog.record(
            "mcp_discover",
            {
                "tool_count": len(tools),
                "resource_count": len(resources),
                "prompt_count": len(prompts),
                "elapsed_ms": round(elapsed_ms, 2),
                "server_name": server_info.get("name", "unknown"),
                "mock": False,
            },
            tenant_id=server.tenant_id,
            server_id=server.id,
        )
        return {"tools": tools, "resources": resources, "prompts": prompts}

    def _mock_discover(self, server: MCPServerRecord) -> dict[str, Any]:
        """Return static mock catalogue. AGENT_MCP_MOCK_MODE=true required."""
        tools = [self.tool_adapter.adapt(t) for t in _MOCK_TOOLS]
        resources = [self.resource_adapter.adapt(r) for r in _MOCK_RESOURCES]
        prompts = [self.prompt_adapter.adapt(p) for p in _MOCK_PROMPTS]

        server.discovered_tools = tools
        server.discovered_resources = resources
        server.discovered_prompts = prompts

        MCPAuditLog.record(
            "mcp_discover",
            {
                "tool_count": len(tools),
                "mock": True,
                "reason": "AGENT_MCP_MOCK_MODE=true",
            },
            tenant_id=server.tenant_id,
            server_id=server.id,
        )
        return {"tools": tools, "resources": resources, "prompts": prompts}

    # ------------------------------------------------------------------
    # Tool approval
    # ------------------------------------------------------------------

    def approve_tool(self, server_id: str, tool_name: str, tenant_id: str | None = None) -> dict[str, Any]:
        """Add tool_name to the server's approved set."""
        server = self._get_server(server_id, tenant_id)
        # Sanitize before adding to approved list
        safe_name = self.security.sanitize_tool({"name": tool_name, "description": ""})["name"]
        server.approved_tools.add(safe_name)
        MCPAuditLog.record(
            "mcp_approve_tool",
            {"tool_name": safe_name},
            tenant_id=server.tenant_id,
            server_id=server_id,
        )
        return {"server_id": server_id, "tool_name": safe_name, "approved": True}

    # ------------------------------------------------------------------
    # Tool call
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an approved MCP tool via the server transport.

        Security checks (in order):
          1. client_enabled
          2. tool in server.approved_tools
          3. external_network (if server is external)
          4. mock mode → synthetic response, no real I/O

        Audit events:
          - mcp_call_attempt  (always, before execution)
          - mcp_call_success  (on success)
          - mcp_call_error    (on failure, exception re-raised)
        """
        self.security.require_client_enabled()
        server = self._get_server(server_id, tenant_id)
        self.security.require_tool_approved(tool_name, server.approved_tools)

        MCPAuditLog.record(
            "mcp_call_attempt",
            {"tool_name": tool_name, "mock": self.security.is_mock_mode()},
            tenant_id=tenant_id or server.tenant_id,
            server_id=server_id,
        )

        # Mock mode
        if self.security.is_mock_mode():
            result = {"mock": True, "tool": tool_name, "result": f"mock result for {tool_name}"}
            MCPAuditLog.record(
                "mcp_call_success",
                {"tool_name": tool_name, "mock": True},
                tenant_id=tenant_id or server.tenant_id,
                server_id=server_id,
            )
            return result

        is_external = self.security.is_external_endpoint(server.endpoint)
        self.security.validate_external_network(is_external)

        transport = build_transport(
            server.transport,
            server.endpoint,
            self._settings.agent_mcp_call_timeout_ms,
        )
        started = time.monotonic()
        try:
            raw = await transport.request(
                "tools/call",
                {"name": tool_name, "arguments": arguments},
            )
            elapsed_ms = (time.monotonic() - started) * 1000
            MCPAuditLog.record(
                "mcp_call_success",
                {
                    "tool_name": tool_name,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "mock": False,
                },
                tenant_id=tenant_id or server.tenant_id,
                server_id=server_id,
            )
            return raw if isinstance(raw, dict) else {"result": raw}
        except Exception as exc:
            MCPAuditLog.record(
                "mcp_call_error",
                {"tool_name": tool_name, "error": str(exc), "mock": False},
                tenant_id=tenant_id or server.tenant_id,
                server_id=server_id,
            )
            raise
        finally:
            await transport.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_server(self, server_id: str, tenant_id: str | None = None) -> MCPServerRecord:
        server = self.registry.get(server_id)
        if not server:
            raise KeyError(f"MCP server '{server_id}' not found")
        if tenant_id and server.tenant_id != tenant_id:
            raise PermissionError(f"Access denied to MCP server '{server_id}' for tenant '{tenant_id}'")
        return server
