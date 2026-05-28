# Owner: agent-platform
import re

from app.core.config import get_settings


class MCPSecurity:
    def __init__(self):
        self.settings = get_settings()

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

    def sanitize_text(self, value: str) -> str:
        value = re.sub(r"(?i)<system>.*?</system>", "", value)
        value = re.sub(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^,\s]+", r"\1=[REDACTED]", value)
        return value.strip()

    def validate_external_network(self, is_external: bool) -> None:
        if is_external and not self.settings.agent_mcp_external_network_enabled:
            raise PermissionError("External MCP network access is disabled by feature flag")

    def validate_sampling(self, wants_sampling: bool) -> None:
        if wants_sampling and not self.settings.agent_mcp_sampling_enabled:
            raise PermissionError("MCP sampling is disabled by default")
