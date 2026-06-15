# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.agents.agent_canary import AgentCanaryAssignment, AgentCanaryPromotionReview
from app.models.agents.agents import AgentDefinition
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CanaryPromotionGate:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def promote(
        self, assignment_id: uuid.UUID, reviewer_id: str, comments: str | None = None
    ) -> dict[str, Any]:
        """
        Promotes a canary agent to the primary position for its tenant.
        """
        assignment = await self.db.get(AgentCanaryAssignment, assignment_id)
        if not assignment or assignment.status != "active":
            raise ValueError("Active canary assignment not found")

        # 1. Record Review
        review = AgentCanaryPromotionReview(
            assignment_id=assignment_id,
            reviewer_id=reviewer_id,
            decision="approve",
            comments=comments,
            eval_summary={"passed": True},  # Mock
        )
        self.db.add(review)

        # 2. Update statuses
        assignment.status = "promoted"

        # In a real implementation, we would update the routing table or AgentDefinition status
        base_agent = await self.db.get(AgentDefinition, assignment.base_agent_id)
        canary_agent = await self.db.get(AgentDefinition, assignment.canary_agent_id)

        if base_agent and canary_agent:
            base_agent.status = "deprecated"
            canary_agent.status = "active"

        await self.db.commit()
        logger.info(
            f"Promoted canary agent {assignment.canary_agent_id} (Assignment {assignment_id})"
        )

        return {"status": "promoted", "new_agent_id": str(assignment.canary_agent_id)}
