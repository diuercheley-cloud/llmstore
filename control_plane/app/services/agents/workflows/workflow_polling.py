import logging
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.agent_workflows_external import AgentWorkflowPollingJob, AgentWorkflowExternalEvent
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from app.core.time import utc_now
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class WorkflowPollingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.signals = WorkflowSignalManager(db)
        self.settings = get_settings()

    async def create_polling_job(
        self, 
        run_id: uuid.UUID, 
        tenant_id: str, 
        url: str, 
        stop_condition: Dict[str, Any],
        interval: int = 60
    ) -> AgentWorkflowPollingJob:
        if not self.settings.agent_workflow_polling_enabled:
            raise HTTPException(status_code=403, detail="Workflow polling is disabled.")

        job = AgentWorkflowPollingJob(
            run_id=run_id,
            tenant_id=tenant_id,
            url=url,
            stop_condition=stop_condition,
            interval_seconds=interval,
            next_poll_at=utc_now() + timedelta(seconds=interval),
            status="active"
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def process_ready_polls(self):
        """
        Background task to process polling jobs that are due.
        """
        stmt = select(AgentWorkflowPollingJob).where(
            AgentWorkflowPollingJob.status == "active",
            AgentWorkflowPollingJob.next_poll_at <= utc_now()
        ).limit(20)
        
        res = await self.db.execute(stmt)
        jobs = res.scalars().all()
        
        for job in jobs:
            await self._execute_poll(job)
            
        await self.db.commit()

    async def _execute_poll(self, job: AgentWorkflowPollingJob):
        job.attempts_count += 1
        logger.info(f"Executing poll {job.id} (attempt {job.attempts_count})")
        
        try:
            # In a real app, use httpx to fetch job.url
            # Mocking response for prototype
            mock_response = {"status": "processing", "progress": job.attempts_count * 10}
            
            # Check stop condition
            condition_path = job.stop_condition.get("path")
            target_value = job.stop_condition.get("value")
            
            if mock_response.get(condition_path) == target_value or job.attempts_count >= job.max_attempts:
                job.status = "completed" if mock_response.get(condition_path) == target_value else "timed_out"
                
                # Signal workflow
                await self.signals.send_signal(
                    run_id=job.run_id,
                    signal_name=f"polling_finished_{job.id}",
                    payload=mock_response
                )
            else:
                # Schedule next with backoff
                delay = int(job.interval_seconds * (job.backoff_multiplier ** (job.attempts_count - 1)))
                job.next_poll_at = utc_now() + timedelta(seconds=delay)
                
        except Exception as e:
            logger.error(f"Poll failed: {str(e)}")
            if job.attempts_count >= job.max_attempts:
                job.status = "failed"
