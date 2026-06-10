# Owner: agent-platform
import logging
from datetime import timedelta

from app.core.time import utc_now
from app.models.agents.agent_workflows import AgentWorkflowRun
from app.services.agents.workflows.workflow_state_machine import WorkflowStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class WorkflowRecoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def recover_stuck_runs(self, timeout_minutes: int = 10):
        """
        Finds workflow runs that are stuck in 'running' state and resets them to 'retry_scheduled'
        or 'pending' so they can be picked up by another worker.
        """
        threshold = utc_now() - timedelta(minutes=timeout_minutes)
        
        stmt = select(AgentWorkflowRun).where(
            AgentWorkflowRun.status == WorkflowStatus.RUNNING.value,
            AgentWorkflowRun.updated_at <= threshold
        )
        
        res = await self.db.execute(stmt)
        stuck_runs = res.scalars().all()
        
        for run in stuck_runs:
            logger.info(f"Recovering stuck workflow run {run.id}")
            run.status = WorkflowStatus.RETRY_SCHEDULED.value
            run.next_execution_at = utc_now()
            # Log recovery event
            from app.models.agents.agent_workflows import AgentWorkflowEvent
            event = AgentWorkflowEvent(
                run_id=run.id,
                event_type="recovery",
                payload={"reason": "stuck_in_running_state", "previous_updated_at": run.updated_at.isoformat()}
            )
            self.db.add(event)
            
        await self.db.commit()
        return len(stuck_runs)
