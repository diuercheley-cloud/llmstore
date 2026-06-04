from enum import Enum


class ConnectorMode(str, Enum):
    MOCK = "mock"
    REAL = "real"

def get_connector_mode() -> ConnectorMode:
    from app.core.config import get_settings
    settings = get_settings()
    mode = str(settings.agent_connector_mode).strip().lower()
    if mode == ConnectorMode.REAL.value:
        return ConnectorMode.REAL
    if mode == ConnectorMode.MOCK.value:
        return ConnectorMode.MOCK
    raise ValueError(
        f"Unsupported AGENT_CONNECTOR_MODE '{settings.agent_connector_mode}'. "
        "Use 'mock' or 'real'."
    )

def is_real_http_enabled() -> bool:
    from app.core.config import get_settings
    settings = get_settings()
    return settings.agent_connector_real_http_enabled
