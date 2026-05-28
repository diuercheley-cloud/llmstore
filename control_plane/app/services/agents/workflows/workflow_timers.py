# Owner: Platform Operations
import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_workflows import AgentWorkflowTimer, AgentWorkflowRun
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class WorkflowTimerManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_timer(self, run_id: uuid.UUID, timer_name: str, delay_seconds: int):
        fire_at = utc_now() + timedelta(seconds=delay_seconds)
        timer = AgentWorkflowTimer(
            run_id=run_id,
            timer_name=timer_name,
            fire_at=fire_at,
            status="pending"
        )
        self.db.add(timer)
        await self.db.commit()
        return timer

    async def get_fired_timers(self):
        stmt = (
            select(AgentWorkflowTimer)
            .where(
                AgentWorkflowTimer.status == "pending",
                AgentWorkflowTimer.fire_at <= utc_now()
            )
            .with_for_update(skip_locked=True)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def mark_fired(self, timer_id: uuid.UUID):
        stmt = select(AgentWorkflowTimer).where(AgentWorkflowTimer.id == timer_id)
        res = await self.db.execute(stmt)
        timer = res.scalar_one_or_none()
        if timer:
            timer.status = "fired"
            await self.db.commit()
