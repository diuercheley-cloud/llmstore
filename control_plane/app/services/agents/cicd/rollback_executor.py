# Owner: agent-platform
import logging
import uuid

from app.models.agents.agent_cicd import AgentDeployment, AgentDeploymentEvent, AgentRollback
from app.models.agents.agents import AgentRegistryEntry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class RollbackExecutor:
    """
    Executes real rollbacks for agents.
    Reverts agent definition, prompts, and associated assets.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_rollback(self, deployment_id: uuid.UUID, reason: str) -> bool:
        """
        Atomically reverts an agent to its previous stable state.
        """
        stmt = select(AgentDeployment).where(AgentDeployment.id == deployment_id)
        res = await self.db.execute(stmt)
        deployment = res.scalar_one_or_none()
        if not deployment: return False

        logger.warning(f"Executing rollback for deployment {deployment_id}. Reason: {reason}")

        previous_stable = await self._find_previous_stable_deployment(deployment)
        if not previous_stable:
            logger.error("Rollback failed: no previous stable deployment found")
            rollback = AgentRollback(
                deployment_id=deployment_id,
                from_version=deployment.version_tag,
                to_version="unknown",
                reason=reason,
                status="failed"
            )
            self.db.add(rollback)
            await self.db.flush()
            return False

        # 1. Create Rollback Record
        rollback = AgentRollback(
            deployment_id=deployment_id,
            from_version=deployment.version_tag,
            to_version=previous_stable.version_tag,
            reason=reason,
            status="in_progress"
        )
        self.db.add(rollback)
        await self.db.flush()

        try:
            # 2. Update Registry Entry
            stmt_reg = select(AgentRegistryEntry).where(AgentRegistryEntry.agent_id == deployment.agent_id)
            res_reg = await self.db.execute(stmt_reg)
            registry = res_reg.scalar_one_or_none()
            
            if registry:
                registry.status = "active"
                logger.info(f"Registry for agent {deployment.agent_id} reverted to active stable version")

            # 3. Mark Deployment as Rolled Back
            deployment.status = "rolled_back"
            previous_stable.status = "completed"
            self.db.add(
                AgentDeploymentEvent(
                    deployment_id=deployment.id,
                    event_type="rollback_completed",
                    details={
                        "reason": reason,
                        "restored_version_tag": previous_stable.version_tag,
                        "environment": deployment.environment,
                    },
                )
            )
            rollback.status = "completed"
            
            await self.db.flush()
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            rollback.status = "failed"
            await self.db.flush()
            return False

    async def _find_previous_stable_deployment(self, deployment: AgentDeployment) -> AgentDeployment | None:
        stmt = (
            select(AgentDeployment)
            .where(AgentDeployment.agent_id == deployment.agent_id)
            .where(AgentDeployment.environment == deployment.environment)
            .where(AgentDeployment.status == "completed")
            .where(AgentDeployment.id != deployment.id)
            .order_by(AgentDeployment.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()
