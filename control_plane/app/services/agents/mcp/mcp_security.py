# Owner: agent-platform
"""
MCP Security

Centralises all MCP security checks:
  - Feature flag gates (require_enabled, require_client_enabled, etc.)
  - External network validation
  - Sampling lock (blocked by default)
  - Tool description / name sanitization (injection prevention)
  - Trust level enforcement for tool approval

Design:
  Every public method either returns silently (check passed) or raises
  PermissionError / ValueError with a human-readable message.
"""

from __future__ import annotations

import re

from app.core.config import get_settings

_DANGEROUS_PATTERNS = [
    r"(?i)<system>.*?</system>",
    r"(?i)<INST>.*?</INST>",
    r"(?i)ignore previous instructions",
    r"(?i)you are now",
    r"(?i)\bprompt injection\b",
]

# Trust levels in ascending order of privilege
_TRUST_LEVELS = ["untrusted", "low", "medium", "high", "admin"]


class MCPSecurity:
    def __init__(self):
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # Feature flag gates
    # ------------------------------------------------------------------

    def require_enabled(self) -> None:
        if not self.settings.agent_mcp_enabled:
            raise PermissionError("MCP is disabled by feature flag")

    def require_client_enabled(self) -> None:
        self.require_enabled()
        if not self.settings.agent_mcp_client_enabled:
            raise PermissionError("MCP client is disabled by feature flag")

    def require_server_enabled(self) -> None:
        self.require_enabled()
        if not self.settings.agent_mcp_server_enabled:
            raise PermissionError("MCP server is disabled by feature flag")

    def require_real_discovery(self) -> None:
        """Raise if real discovery is disabled (only mock would be available)."""
        self.require_client_enabled()
        if not self.settings.agent_mcp_real_discovery_enabled:
            raise PermissionError(
                "Real MCP discovery is disabled: AGENT_MCP_REAL_DISCOVERY_ENABLED=false"
            )

    def is_mock_mode(self) -> bool:
        if self.settings.app_env == "production" and self.settings.agent_mcp_mock_mode:
            raise PermissionError("MCP mock mode is not allowed in production environments.")
        return self.settings.agent_mcp_mock_mode

    # ------------------------------------------------------------------
    # Network validation
    # ------------------------------------------------------------------

    def validate_external_network(self, is_external: bool) -> None:
        if is_external and not self.settings.agent_mcp_external_network_enabled:
            raise PermissionError("External MCP network access is disabled by feature flag")

    def is_external_endpoint(self, endpoint: str) -> bool:
        return not (
            endpoint.startswith("http://localhost")
            or endpoint.startswith("http://127.")
            or endpoint.startswith("http://0.0.0.0")
            or endpoint.startswith("stdio:")
        )

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def validate_sampling(self, wants_sampling: bool) -> None:
        if wants_sampling and not self.settings.agent_mcp_sampling_enabled:
            raise PermissionError("MCP sampling is disabled by default")

    # ------------------------------------------------------------------
    # Text sanitization
    # ------------------------------------------------------------------

    def sanitize_text(self, value: str) -> str:
        """Remove prompt-injection patterns and secrets from arbitrary text."""
        for pattern in _DANGEROUS_PATTERNS:
            value = re.sub(pattern, "[REMOVED]", value, flags=re.DOTALL)
        value = re.sub(
            r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^,\s]+",
            r"\1=[REDACTED]",
            value,
        )
        return value.strip()

    def sanitize_tool(self, tool: dict) -> dict:
        """Sanitize name and description of a tool record returned by a server."""
        return {
            **tool,
            "name": re.sub(r"[^a-zA-Z0-9_\-]", "_", tool.get("name", ""))[:64],
            "description": self.sanitize_text(tool.get("description", ""))[:1024],
        }

    # ------------------------------------------------------------------
    # Trust and approval
    # ------------------------------------------------------------------

    def require_trust_level(self, server_trust: str, required: str) -> None:
        """Check server trust level >= required level."""
        try:
            if _TRUST_LEVELS.index(server_trust) < _TRUST_LEVELS.index(required):
                raise PermissionError(
                    f"Server trust level '{server_trust}' is below required '{required}'"
                )
        except ValueError:
            raise ValueError(f"Unknown trust level: '{server_trust}' or '{required}'")

    def require_tool_approved(self, tool_name: str, approved_tools: set[str]) -> None:
        """Block execution of unapproved tools."""
        if tool_name not in approved_tools:
            raise PermissionError(
                f"MCP tool '{tool_name}' is not in the approved list for this server. "
                "An admin must call POST /admin/agents/mcp/servers/{id}/approve-tool first."
            )

    def validate_tool_schema(self, tool: dict) -> None:
        """Basic structural validation of a tool record from a server."""
        if not tool.get("name"):
            raise ValueError("MCP tool missing required field 'name'")
        if not isinstance(tool.get("inputSchema") or tool.get("input_schema") or {}, dict):
            raise ValueError(f"MCP tool '{tool['name']}' has invalid inputSchema")
