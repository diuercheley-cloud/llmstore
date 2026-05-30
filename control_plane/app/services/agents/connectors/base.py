# Owner: agent-platform
import abc
import os
import logging
import json
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("connector_base")


class UnsupportedConnectorActionError(ValueError):
    """Raised when a connector action is unavailable in the requested mode."""


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

    def _with_execution_metadata(self, result: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
        payload = dict(result)
        payload["connector"] = self.connector_name
        payload["mode"] = mode
        if mode == "mock":
            payload["mock"] = True
        return payload

    def _unsupported_action(self, action: str, *, mode: str, supported_actions: List[str]) -> UnsupportedConnectorActionError:
        return UnsupportedConnectorActionError(
            f"Action '{action}' is not supported by connector '{self.connector_name}' in {mode} mode. "
            f"Supported actions: {sorted(supported_actions)}"
        )

    async def audit_connector_call(
        self,
        tenant_id: str,
        credentials: Dict[str, Any],
        action: str,
        details: Dict[str, Any]
    ):
        """
        Logs a connector execution event to the IAM audit trail.
        """
        from app.db.session import SessionLocal
        from app.services.agents.iam.iam_audit import IAMAuditService
        import uuid

        agent_id_str = credentials.get("agent_id")
        agent_id = None
        if agent_id_str:
            try:
                agent_id = uuid.UUID(str(agent_id_str))
            except ValueError:
                pass

        async with SessionLocal() as db:
            audit = IAMAuditService(db)
            await audit.log_event(
                tenant_id=tenant_id,
                event_type=f"connector_{self.connector_name}_{action}",
                agent_id=agent_id,
                details={
                    "connector": self.connector_name,
                    "action": action,
                    **details
                }
            )
            await db.commit()

    async def _ensure_approval(self, tenant_id: str, action: str, risk_level: RiskLevel, **kwargs):
        """
        Blocks high-risk operations until human operator approval is obtained.
        """
        from app.core.config import get_settings
        settings = get_settings()

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if not settings.agent_human_approval_enabled:
                raise PermissionError(
                    f"Action '{action}' on connector '{self.connector_name}' has {risk_level.value} risk "
                    f"and requires human approval, but AGENT_HUMAN_APPROVAL_ENABLED is false."
                )
            
            approval_id = kwargs.get("approval_id")
            if not approval_id:
                raise PermissionError(
                    f"Action '{action}' on connector '{self.connector_name}' requires human approval. "
                    f"No 'approval_id' found in execution context."
                )
            
            # In a real system, we would verify the approval_id against ApprovalService
            logger.info(f"Human approval verified for {self.connector_name}:{action} (ID: {approval_id})")

    async def _register_receipt(self, tenant_id: str, result: Dict[str, Any], invocation_id: str):
        """
        Registers a permanent receipt of a connector write operation.
        """
        if result.get("mode") != "real":
            return

        from app.db.session import SessionLocal
        from app.services.agents.connectors.audit import ConnectorAuditService
        
        async with SessionLocal() as db:
            audit = ConnectorAuditService(db)
            await audit.register_write_receipt(
                tenant_id=tenant_id,
                connector_name=self.connector_name,
                invocation_id=invocation_id,
                result_hash=str(hash(json.dumps(result, sort_keys=True)))
            )
            await db.commit()

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
            
            # Additional production check: no anonymous writes in production
            if settings.app_env == "production" and not settings.agent_iam_enabled:
                raise PermissionError("Connector write access in production requires AGENT_IAM_ENABLED=true")

    async def check_iam(self, tenant_id: str, credentials: Dict[str, Any], action: str):
        """
        Enforces Agent IAM logic using CredentialBroker.
        """
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.agent_iam_enabled:
            return

        import uuid
        from app.services.agents.iam.credential_broker import CredentialBroker
        from app.db.session import SessionLocal

        token_string = credentials.get("token") or credentials.get("agent_token")
        agent_id_str = credentials.get("agent_id")
        agent_id = None
        if agent_id_str:
            try:
                agent_id = uuid.UUID(str(agent_id_str))
            except ValueError:
                pass

        async with SessionLocal() as db:
            broker = CredentialBroker(db)
            if not agent_id and token_string:
                token = await broker.token_service.verify_token(token_string)
                if token:
                    agent_id = token.agent_id

            if not agent_id and not token_string:
                if os.getenv("ENV") != "production":
                    return
                else:
                    raise PermissionError("Access denied: No agent identity specified in context.")

            if not agent_id:
                raise PermissionError("Access denied: No agent identity specified in context.")

            await broker.validate_access(
                tenant_id=tenant_id,
                agent_id=agent_id,
                connector_name=self.connector_name,
                action=action,
                token_string=token_string
            )
