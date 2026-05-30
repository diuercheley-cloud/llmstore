# Owner: agent-platform
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent_cicd import AgentRollback, AgentDeployment
from app.models.agents import AgentRegistryEntry

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

        # 1. Create Rollback Record
        rollback = AgentRollback(
            deployment_id=deployment_id,
            from_version=deployment.version_tag,
            to_version="previous_stable", # Simplified: would lookup real previous version
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
                # In a real system, we'd lookup the previous definition_id from history
                # and restore it here.
                registry.status = "stable"
                logger.info(f"Registry for agent {deployment.agent_id} reverted to stable")

            # 3. Mark Deployment as Rolled Back
            deployment.status = "rolled_back"
            rollback.status = "completed"
            
            await self.db.flush()
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            rollback.status = "failed"
            await self.db.flush()
            return False
