import logging
import uuid

from app.models.agents.agent_iam import AgentDelegatedToken

logger = logging.getLogger(__name__)


class AgentScopeManager:
    @staticmethod
    def match_scope(
        token: AgentDelegatedToken,
        tenant_id: str,
        agent_id: uuid.UUID,
        connector_name: str,
        action: str,
    ) -> bool:
        """
        Validates that a token:
        1. Belongs to the correct tenant (strictly prevents cross-tenant access).
        2. Belongs to the correct agent.
        3. Covers the requested connector and action.
        """
        # 1. Tenant boundary enforcement
        if token.tenant_id != tenant_id:
            logger.warning(
                f"Tenant mismatch: Token tenant {token.tenant_id} != Requested tenant {tenant_id}"
            )
            return False

        # 2. Agent boundary enforcement
        if token.agent_id != agent_id:
            logger.warning(
                f"Agent mismatch: Token agent {token.agent_id} != Requested agent {agent_id}"
            )
            return False

        # 3. Scope match (supports wildcards '*')
        for scope in token.scopes:
            conn_pattern = scope.get("connector", "")
            act_pattern = scope.get("action", "")

            conn_ok = (conn_pattern == "*") or (conn_pattern.lower() == connector_name.lower())
            act_ok = (act_pattern == "*") or (act_pattern.lower() == action.lower())

            if conn_ok and act_ok:
                return True

        logger.warning(
            f"Scope mismatch: Token scopes {token.scopes} do not cover connector '{connector_name}' / action '{action}'"
        )
        return False
