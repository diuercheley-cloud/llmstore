import abc
import os
from typing import Any, Dict, List, Optional
from enum import Enum

class ConnectorCapability(str, Enum):
    READ = "read"
    WRITE = "write"
    COMMENT = "comment"
    SEARCH = "search"
    CREATE = "create"
    UPDATE = "update"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SideEffectLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"

class ConnectorAdapter(abc.ABC):
    """
    Base contract for SaaS Connectors in the Agentic AI Platform.
    """

    @property
    @abc.abstractmethod
    def connector_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def connector_version(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def provider(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def capabilities(self) -> List[ConnectorCapability]:
        pass

    @property
    @abc.abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass

    @property
    @abc.abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        pass

    @property
    @abc.abstractmethod
    def required_scopes(self) -> List[str]:
        pass

    @property
    @abc.abstractmethod
    def risk_level(self) -> RiskLevel:
        pass

    @property
    @abc.abstractmethod
    def side_effect_level(self) -> SideEffectLevel:
        pass

    @property
    def dry_run_supported(self) -> bool:
        return True

    @property
    def rollback_supported(self) -> bool:
        return False

    @property
    @abc.abstractmethod
    def rate_limit_policy(self) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def healthcheck(self) -> bool:
        pass

    @abc.abstractmethod
    async def dry_run(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def execute(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        pass

    async def rollback(self, tenant_id: str, credentials: Dict[str, Any], invocation_id: str, **kwargs) -> Dict[str, Any]:
        if not self.rollback_supported:
            return {"status": "error", "message": "Rollback not supported for this connector"}
        raise NotImplementedError("Rollback must be implemented if rollback_supported is True")

    def _check_feature_flags(self, capability: ConnectorCapability):
        """
        Enforces governance via feature flags.
        """
        from app.core.config import get_settings
        settings = get_settings()

        # Global enabled check
        if not settings.agent_saas_connectors_enabled:
            raise PermissionError("SaaS Connectors are globally disabled (AGENT_SAAS_CONNECTORS_ENABLED=false)")

        # External network check
        if not settings.agent_connector_external_network_enabled:
            raise PermissionError("External network access for connectors is disabled (AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED=false)")

        # Write check
        write_capabilities = [ConnectorCapability.WRITE, ConnectorCapability.CREATE, ConnectorCapability.UPDATE, ConnectorCapability.COMMENT]
        if capability in write_capabilities:
            if not settings.agent_connector_write_enabled:
                raise PermissionError(f"Write capability '{capability.value}' is disabled (AGENT_CONNECTOR_WRITE_ENABLED=false)")
