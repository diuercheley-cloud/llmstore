from typing import Any, Dict

from app.services.agents.connectors.connector_mode import (
    ConnectorMode,
    get_connector_mode,
    is_real_http_enabled,
)


class ConnectorRuntime:
    @staticmethod
    def get_mode(connector_name: str) -> ConnectorMode:
        from app.core.config import get_settings
        settings = get_settings()
        
        # Check if specific connector is enabled for real mode
        flag_name = f"agent_{connector_name.lower()}_connector_enabled"
        connector_enabled = getattr(settings, flag_name, False)
        
        if get_connector_mode() == ConnectorMode.REAL and connector_enabled:
            return ConnectorMode.REAL
        return ConnectorMode.MOCK

    @staticmethod
    def ensure_real_allowed(connector_name: str):
        if ConnectorRuntime.get_mode(connector_name) == ConnectorMode.REAL:
            if not is_real_http_enabled():
                raise PermissionError(
                    f"Real HTTP calls are disabled globally (AGENT_CONNECTOR_REAL_HTTP_ENABLED=false). "
                    f"Cannot execute real call for {connector_name}."
                )
        else:
            # If we are in mock mode but somehow trying to do something real (shouldn't happen with the mode check)
            pass

    @staticmethod
    def validate_credentials(connector_name: str, credentials: Dict[str, Any]):
        if ConnectorRuntime.get_mode(connector_name) == ConnectorMode.REAL:
            if not credentials or not any(k in credentials for k in ["token", "api_key", "password"]):
                raise ValueError(f"Missing required credentials for real mode in {connector_name} connector")
