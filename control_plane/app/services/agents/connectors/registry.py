# Owner: agent-platform
import logging

from app.services.agents.connectors.base import ConnectorAdapter

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for SaaS Connectors.
    """

    _instance = None
    _connectors: dict[str, ConnectorAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, connector: ConnectorAdapter) -> None:
        if not connector.connector_name:
            raise ValueError("Connector must have a name.")

        logger.info(
            f"Registering SaaS connector: {connector.connector_name} (v{connector.connector_version})"
        )
        self._connectors[connector.connector_name] = connector

    def get_connector(self, name: str) -> ConnectorAdapter | None:
        return self._connectors.get(name)

    def list_connectors(self) -> list[ConnectorAdapter]:
        return list(self._connectors.values())

    def clear(self) -> None:
        self._connectors.clear()


connector_registry = ConnectorRegistry()
