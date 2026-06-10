# Owner: agent-platform
import logging
import uuid

from app.core.time import utc_now
from app.models.agents.agents import AgentCompensationAction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class CompensationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_compensation(self, task_id: uuid.UUID, action_type: str, payload: dict) -> AgentCompensationAction:
        action = AgentCompensationAction(
            task_id=task_id,
            action_type=action_type,
            payload=payload,
            status="pending"
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def trigger_compensation(self, task_id: uuid.UUID):
        stmt = select(AgentCompensationAction).where(
            AgentCompensationAction.task_id == task_id,
            AgentCompensationAction.status == "pending"
        )
        res = await self.db.execute(stmt)
        actions = res.scalars().all()
        
        for action in actions:
            try:
                logger.info(f"Executing compensation action {action.id} for task {task_id}")
                # Reversal logic would go here
                action.status = "executed"
                action.executed_at = utc_now()
            except Exception:
                logger.exception(f"Compensation action {action.id} failed")
                action.status = "failed"
            
            await self.db.commit()
