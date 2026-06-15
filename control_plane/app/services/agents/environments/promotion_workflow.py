import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.agents.agent_environments import AgentPromotionRequest
from app.services.agents.environments.agent_environments import AgentEnvironmentsService
from app.services.agents.environments.environment_policy import EnvironmentPolicyService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("promotion_workflow")


class PromotionWorkflowService:
    @classmethod
    async def create_promotion_request(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        from_env: str,
        to_env: str,
        version_id: str,
        requested_by: str,
    ) -> AgentPromotionRequest:
        """Creates a promotion request. Staging/dev promotions are auto-approved, production is pending."""
        agent_uuid = uuid.UUID(agent_id)
        version_uuid = uuid.UUID(version_id)
        to_env_lower = to_env.lower().strip()

        status = "pending"
        approved_by = None
        approved_at = None

        if to_env_lower != "production":
            status = "approved"
            approved_by = "system"
            approved_at = datetime.now(UTC)

        # Resolve registry entry first
        from app.models.agents.agents import AgentRegistryEntry

        stmt_reg = select(AgentRegistryEntry).where(
            (AgentRegistryEntry.id == agent_uuid) | (AgentRegistryEntry.agent_id == agent_uuid)
        )
        res_reg = await db.execute(stmt_reg)
        reg = res_reg.scalar_one_or_none()
        if not reg:
            raise ValueError("Agent registry entry not found.")

        req = AgentPromotionRequest(
            tenant_id=tenant_id,
            agent_id=reg.id,
            from_environment=from_env.lower().strip(),
            to_environment=to_env_lower,
            version_id=version_uuid,
            status=status,
            requested_by=requested_by,
            approved_by=approved_by,
            approved_at=approved_at,
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req

    @classmethod
    async def approve_promotion_request(
        cls, db: AsyncSession, tenant_id: str, request_id: str, approved_by: str
    ) -> dict[str, Any]:
        """Approves a pending promotion request, allowing it to be executed."""
        try:
            req_uuid = uuid.UUID(request_id)
        except ValueError:
            return {"status": "error", "message": "Invalid request ID format."}

        stmt = select(AgentPromotionRequest).where(
            AgentPromotionRequest.id == req_uuid, AgentPromotionRequest.tenant_id == tenant_id
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()

        if not req:
            return {"status": "error", "message": "Promotion request not found."}

        if req.status != "pending":
            return {
                "status": "error",
                "message": f"Cannot approve request with status: {req.status}",
            }

        req.status = "approved"
        req.approved_by = approved_by
        req.approved_at = datetime.now(UTC)
        await db.commit()

        return {
            "status": "success",
            "message": "Promotion request approved successfully.",
            "request_id": str(req.id),
        }

    @classmethod
    async def execute_promotion(
        cls, db: AsyncSession, tenant_id: str, request_id: str
    ) -> dict[str, Any]:
        """Executes an approved promotion request by evaluating policies and deploying the version."""
        try:
            req_uuid = uuid.UUID(request_id)
        except ValueError:
            return {"status": "error", "message": "Invalid request ID format."}

        stmt = select(AgentPromotionRequest).where(
            AgentPromotionRequest.id == req_uuid, AgentPromotionRequest.tenant_id == tenant_id
        )
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()

        if not req:
            return {"status": "error", "message": "Promotion request not found."}

        if req.status != "approved":
            return {
                "status": "error",
                "message": f"Cannot execute promotion request in status: {req.status}. Must be approved.",
            }

        # Validate policies for the deployment
        allowed, reason = await EnvironmentPolicyService.validate_promotion(
            db=db,
            tenant_id=tenant_id,
            agent_id=str(req.agent_id),
            version_id=str(req.version_id),
            to_environment=req.to_environment,
            promotion_req_id=str(req.id),
        )

        if not allowed:
            req.status = "rejected"
            req.promotion_metadata = {"failure_reason": reason}
            await db.commit()
            return {"status": "policy_denied", "message": f"Policy check failed: {reason}"}

        # Deploy
        await AgentEnvironmentsService.deploy_to_environment(
            db=db,
            tenant_id=tenant_id,
            agent_id=req.agent_id,
            version_id=req.version_id,
            environment=req.to_environment,
        )

        req.status = "executed"
        await db.commit()

        return {
            "status": "success",
            "message": f"Agent version promoted to {req.to_environment} environment successfully.",
            "deployed_version_id": str(req.version_id),
        }
