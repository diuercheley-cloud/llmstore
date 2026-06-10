import logging
from typing import Optional

from app.models.agents.agent_environments import AgentPromotionRequest
from app.models.agents.agents import AgentDefinition, AgentEvalBaseline, AgentEvalGateResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("environment_policy")


class EnvironmentPolicyService:
    @classmethod
    async def validate_promotion(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        version_id: str,
        to_environment: str,
        promotion_req_id: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validates if the target agent definition / version meets the policy constraints
        for deployment to dev, staging, or production.
        """
        import uuid
        agent_uuid = uuid.UUID(agent_id)
        version_uuid = uuid.UUID(version_id)

        # Retrieve Agent Definition (which acts as the specific immutable agent version config)
        stmt_def = select(AgentDefinition).where(
            AgentDefinition.id == version_uuid,
            AgentDefinition.tenant_id == tenant_id
        )
        res_def = await db.execute(stmt_def)
        agent_def = res_def.scalar_one_or_none()
        if not agent_def:
            return False, "Agent definition version not found."

        # Resolve registry entry first
        from app.models.agents.agents import AgentRegistryEntry
        stmt_reg = select(AgentRegistryEntry).where(
            (AgentRegistryEntry.id == agent_uuid) | (AgentRegistryEntry.agent_id == agent_uuid)
        )
        res_reg = await db.execute(stmt_reg)
        reg = res_reg.scalar_one_or_none()
        if not reg:
            return False, "Agent registry entry not found."

        to_env_lower = to_environment.lower().strip()

        if to_env_lower == "dev":
            # Dev allows everything (mock / dry run)
            return True, None

        elif to_env_lower == "staging":
            # Staging requires evaluations to have passed
            stmt_eval = select(AgentEvalGateResult).where(
                AgentEvalGateResult.agent_id == reg.id,
                AgentEvalGateResult.passed == True
            )
            res_eval = await db.execute(stmt_eval)
            evals_passed = res_eval.scalars().first()
            if not evals_passed:
                return False, "Evals check failed: No successful evaluation gate results found for this agent."
            return True, None

        elif to_env_lower == "production":
            # Production requires:
            # 1. Eval baseline
            stmt_baseline = select(AgentEvalBaseline).where(
                AgentEvalBaseline.agent_id == reg.id
            )
            res_baseline = await db.execute(stmt_baseline)
            baseline = res_baseline.scalar_one_or_none()
            if not baseline:
                return False, "Production policy violation: Eval baseline must be defined."

            # 2. Security checks (no secrets in instructions, no forbidden patterns)
            instructions = agent_def.instructions or ""
            # Simple check for aws secrets or private keys in agent instructions
            import re
            secret_patterns = [
                r"(?i)(password|secret|api_key|apikey|token|private_key)\s*[:=]\s*[a-zA-Z0-9_\-\.\~]{8,}",
                r"-----BEGIN[ A-Z0-9_]*PRIVATE KEY-----"
            ]
            for pattern in secret_patterns:
                if re.search(pattern, instructions):
                    return False, "Security check failed: Agent instructions contain sensitive credentials or private keys."

            # 3. Approval: there must be an approved promotion request
            if promotion_req_id:
                stmt_req = select(AgentPromotionRequest).where(
                    AgentPromotionRequest.id == uuid.UUID(promotion_req_id),
                    AgentPromotionRequest.status == "approved"
                )
                res_req = await db.execute(stmt_req)
                approved = res_req.scalar_one_or_none()
                if not approved:
                    return False, "Production deployment denied: Promotion request has not been approved."
            else:
                # Query if there is ANY approved promotion request for this version to production
                stmt_req = select(AgentPromotionRequest).where(
                    AgentPromotionRequest.agent_id == reg.id,
                    AgentPromotionRequest.version_id == version_uuid,
                    AgentPromotionRequest.to_environment == "production",
                    AgentPromotionRequest.status == "approved"
                )
                res_req = await db.execute(stmt_req)
                approved = res_req.scalars().first()
                if not approved:
                    return False, "Production deployment denied: Requires an approved promotion request."

            # 4. No Mock LLM provider allowed in production
            model_id = (agent_def.model_id or "").lower()
            if "mock" in model_id or "dummy" in model_id:
                return False, "Production policy violation: Mock model providers are prohibited in production."

            # 5. Rollback point check (handled during promotion deployment by capturing current production version as previous)
            return True, None

        else:
            return False, f"Unknown deployment environment: {to_environment}"
