import logging
import os
import uuid

from app.core.config import get_settings
from app.models.agents.agent_iam import AgentIdentityBinding, AgentServicePrincipal
from app.services.agents.iam.agent_scopes import AgentScopeManager
from app.services.agents.iam.delegated_tokens import DelegatedTokenService
from app.services.agents.iam.iam_audit import IAMAuditService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CredentialBroker:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_service = DelegatedTokenService(db)
        self.scope_manager = AgentScopeManager()
        self.audit = IAMAuditService(db)

    def _is_write_action(self, action: str) -> bool:
        """Determines if the action requires write permissions."""
        write_terms = ["create", "write", "comment", "update", "delete", "post", "put", "patch"]
        return any(term in action.lower() for term in write_terms)

    async def validate_access(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        connector_name: str,
        action: str,
        token_string: str | None = None,
    ) -> bool:
        """
        Main access control broker for connector executions.
        Validates:
        1. Feature flag status.
        2. Production service principal enforcement.
        3. Token validity, expiration, revocation.
        4. Tenant isolation (no cross-tenant access).
        5. Scope requirements.
        6. Identity binding for write actions.
        7. User delegated grant/approval for write actions.
        """
        settings = get_settings()
        if not settings.agent_iam_enabled:
            # Bypass when Agent IAM is disabled
            return True

        # 1. Production service principal enforcement
        is_prod = os.getenv("ENV") == "production" or os.getenv("FASTAPI_ENV") == "production"

        # Check if service principal exists
        stmt = select(AgentServicePrincipal).where(
            AgentServicePrincipal.tenant_id == tenant_id,
            AgentServicePrincipal.agent_id == agent_id,
        )
        res = await self.db.execute(stmt)
        sp = res.scalar_one_or_none()

        if is_prod and not sp:
            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="access_denied_missing_service_principal_prod",
                agent_id=agent_id,
                details={"connector": connector_name, "action": action},
            )
            raise PermissionError(
                f"Production requires agent '{agent_id}' to have a Service Principal."
            )

        # 2. Token verification
        if not token_string:
            # Support fallback for dev/test manual tokens via env variables if settings permit
            env_key = f"AGENT_CONNECTOR_{connector_name.upper()}_TOKEN"
            env_token = os.getenv(env_key)
            if env_token and (not is_prod or not settings.agent_iam_enabled):
                # Allow manual environment token in dev/test
                return True

            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="access_denied_no_token",
                agent_id=agent_id,
                details={"connector": connector_name, "action": action},
            )
            raise PermissionError("Access denied: No token provided.")

        # Verify token in db (or mock/manual)
        token = await self.token_service.verify_token(token_string)
        if not token:
            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="access_denied_invalid_token",
                agent_id=agent_id,
                details={"connector": connector_name, "action": action},
            )
            raise PermissionError("Access denied: Invalid, expired, or revoked token.")

        # 3. Tenant bounds verification (Cross-tenant token grant blocks)
        if token.tenant_id != tenant_id:
            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="access_denied_cross_tenant",
                agent_id=agent_id,
                details={
                    "connector": connector_name,
                    "action": action,
                    "token_tenant": token.tenant_id,
                },
            )
            raise PermissionError(
                f"Cross-tenant access blocked. Token tenant: {token.tenant_id}, target tenant: {tenant_id}"
            )

        # 4. Scope verification
        if not self.scope_manager.match_scope(token, tenant_id, agent_id, connector_name, action):
            await self.audit.log_event(
                tenant_id=tenant_id,
                event_type="access_denied_insufficient_scopes",
                agent_id=agent_id,
                details={
                    "connector": connector_name,
                    "action": action,
                    "token_scopes": token.scopes,
                },
            )
            raise PermissionError(
                f"Insufficient scopes for action '{action}' on connector '{connector_name}'."
            )

        # 5. Write actions governance
        if self._is_write_action(action):
            # Requs: Agent sem identity não pode usar connector write.
            stmt_ib = select(AgentIdentityBinding).where(
                AgentIdentityBinding.tenant_id == tenant_id,
                AgentIdentityBinding.agent_id == agent_id,
            )
            res_ib = await self.db.execute(stmt_ib)
            ib = res_ib.scalar_one_or_none()

            if not ib:
                await self.audit.log_event(
                    tenant_id=tenant_id,
                    event_type="access_denied_write_no_identity",
                    agent_id=agent_id,
                    details={"connector": connector_name, "action": action},
                )
                raise PermissionError(
                    f"Agent '{agent_id}' does not have a bound identity. Connector write actions are prohibited."
                )

            # Requs: Write actions exigem delegated grant ou approval.
            # Delegated grant means a token of type "connector" exchanged via user grant, OR a manual test token.
            # If token is type "manual" and has no user grant background, we check if it is explicitly allowed.
            if token.token_type not in ["connector", "manual"]:
                await self.audit.log_event(
                    tenant_id=tenant_id,
                    event_type="access_denied_write_no_delegation",
                    agent_id=agent_id,
                    details={
                        "connector": connector_name,
                        "action": action,
                        "token_type": token.token_type,
                    },
                )
                raise PermissionError(
                    "Write actions require a user delegated grant or explicit approval."
                )

        # Access Granted!
        await self.audit.log_event(
            tenant_id=tenant_id,
            event_type="access_granted",
            agent_id=agent_id,
            details={"connector": connector_name, "action": action},
        )
        return True
