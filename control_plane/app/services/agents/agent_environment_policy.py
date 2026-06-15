"""
Owner: agent-platform
Status: beta
"""

import logging
import uuid

from app.core.time import utc_now
from app.models.agents.agents import AgentEnvironmentPolicy, AgentPolicyException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class AgentEnvironmentPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_policy(
        self, environment: str, tenant_id: str | None = None
    ) -> AgentEnvironmentPolicy:
        # Check for tenant-specific policy first
        if tenant_id:
            res = await self.db.execute(
                select(AgentEnvironmentPolicy)
                .where(AgentEnvironmentPolicy.environment == environment)
                .where(AgentEnvironmentPolicy.tenant_id == tenant_id)
                .where(AgentEnvironmentPolicy.is_active == True)
            )
            policy = res.scalar_one_or_none()
            if policy:
                return policy

        # Fallback to global policy for environment
        res = await self.db.execute(
            select(AgentEnvironmentPolicy)
            .where(AgentEnvironmentPolicy.environment == environment)
            .where(AgentEnvironmentPolicy.tenant_id.is_(None))
            .where(AgentEnvironmentPolicy.is_active == True)
        )
        policy = res.scalar_one_or_none()
        if not policy:
            # Return default policy
            return AgentEnvironmentPolicy(
                environment=environment,
                config_json={
                    "require_approval": environment == "production",
                    "require_eval_baseline": environment == "production",
                    "allow_external_tools": environment != "sovereign",
                },
            )
        return policy

    async def check_tool_access(
        self, agent_id: uuid.UUID, tool_name: str, environment: str
    ) -> bool:
        policy = await self.get_policy(environment)

        # 1. Sovereign environment check
        if environment == "sovereign":
            if not policy.config_json.get("allow_external_tools", False):
                # Check if it's an external tool (mock check)
                if tool_name.startswith("external_"):
                    return await self._has_valid_exception(agent_id, "sovereign_tool_block")

        # 2. Destructive tool check
        destructive_tools = ["write", "delete", "destroy"]
        if any(dt in tool_name.lower() for dt in destructive_tools):
            # We might require a specific role here, but that's handled by RBAC usually.
            # Here we check if the environment allows it.
            if not policy.config_json.get("allow_destructive_tools", True):
                return await self._has_valid_exception(agent_id, "destructive_tool_block")

        return True

    async def _has_valid_exception(self, agent_id: uuid.UUID, policy_type: str) -> bool:
        res = await self.db.execute(
            select(AgentPolicyException)
            .where(AgentPolicyException.agent_id == agent_id)
            .where(AgentPolicyException.policy_type == policy_type)
            .where(AgentPolicyException.expires_at > utc_now())
        )
        exception = res.scalar_one_or_none()
        return exception is not None

    async def create_exception(
        self,
        agent_id: uuid.UUID,
        policy_type: str,
        reason: str,
        approved_by: str,
        ttl_hours: int = 24,
    ) -> AgentPolicyException:
        from datetime import timedelta

        exception = AgentPolicyException(
            agent_id=agent_id,
            policy_type=policy_type,
            exception_reason=reason,
            approved_by=approved_by,
            expires_at=utc_now() + timedelta(hours=ttl_hours),
            created_at=utc_now(),
        )
        self.db.add(exception)
        await self.db.commit()
        await self.db.refresh(exception)
        return exception
