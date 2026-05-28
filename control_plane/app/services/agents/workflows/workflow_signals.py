# Owner: Platform Operations
import uuid
import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_workflows import AgentWorkflowSignal, AgentWorkflowRun
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class WorkflowSignalManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_signal(self, run_id: uuid.UUID, signal_name: str, payload: Dict[str, Any]):
        signal = AgentWorkflowSignal(
            run_id=run_id,
            signal_name=signal_name,
            payload=payload,
            status="pending"
        )
        self.db.add(signal)
        
        # Also wake up the workflow if it was waiting for signal
        stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if run and run.status in {"waiting_signal", "sleeping", "waiting_approval", "waiting_webhook"}:
            run.status = "running"
            run.next_execution_at = utc_now()
            
        await self.db.commit()
        return signal

    async def consume_signal(self, signal_id: uuid.UUID):
        stmt = select(AgentWorkflowSignal).where(AgentWorkflowSignal.id == signal_id)
        res = await self.db.execute(stmt)
        signal = res.scalar_one_or_none()
        if signal:
            signal.status = "consumed"
            await self.db.commit()
            return signal
        return None

    async def get_pending_signals(self, run_id: uuid.UUID):
        stmt = select(AgentWorkflowSignal).where(
            AgentWorkflowSignal.run_id == run_id,
            AgentWorkflowSignal.status == "pending"
        ).order_by(AgentWorkflowSignal.created_at.asc())
        res = await self.db.execute(stmt)
        return res.scalars().all()
