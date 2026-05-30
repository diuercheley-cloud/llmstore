"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_execution import (
    AgentExecutionJob,
    AgentWorkerHeartbeat,
    AgentExecutionLease,
    AgentExecutionDeadLetter,
)
from app.services.agents.agent_queue import AgentQueueManager, update_queue_metrics
from app.services.agents.agent_cancellation import AgentCancellationService
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class AgentExecutionPlane:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.queue_mgr = AgentQueueManager(db)

    def _verify_enabled(self):
        if not self.settings.agent_execution_plane_enabled:
            raise RuntimeError("Agent Execution Plane is disabled.")

    async def get_jobs(self, tenant_id: str | None = None) -> List[AgentExecutionJob]:
        self._verify_enabled()
        stmt = select(AgentExecutionJob)
        if tenant_id:
            stmt = stmt.where(AgentExecutionJob.tenant_id == tenant_id)
        stmt = stmt.order_by(AgentExecutionJob.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_workers(self) -> List[AgentWorkerHeartbeat]:
        self._verify_enabled()
        stmt = select(AgentWorkerHeartbeat).order_by(AgentWorkerHeartbeat.last_heartbeat.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_dead_letters(self, tenant_id: str | None = None) -> List[AgentExecutionDeadLetter]:
        self._verify_enabled()
        stmt = select(AgentExecutionDeadLetter)
        if tenant_id:
            stmt = stmt.where(AgentExecutionDeadLetter.tenant_id == tenant_id)
        stmt = stmt.order_by(AgentExecutionDeadLetter.failed_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def cancel_job(self, job_id: uuid.UUID, tenant_id: str | None = None) -> bool:
        self._verify_enabled()
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return False
        
        # Tenant boundary check
        if tenant_id and job.tenant_id != tenant_id:
            raise PermissionError("Access denied to this job.")

        return await AgentCancellationService.cancel_job(self.db, job_id)

    async def retry_job(self, job_id: uuid.UUID, tenant_id: str | None = None) -> bool:
        self._verify_enabled()
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id).with_for_update()
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return False

        # Tenant boundary check
        if tenant_id and job.tenant_id != tenant_id:
            raise PermissionError("Access denied to this job.")

        if job.queue_status not in ("failed", "dead_letter", "cancelled"):
            logger.warning(f"Cannot retry job {job_id} in status {job.queue_status}")
            return False

        # Reset attempts, schedule to run immediately
        job.attempt_count = 0
        job.queue_status = "queued"
        job.available_at = utc_now()
        job.updated_at = utc_now()

        # Update run status to queued
        await agent_state.update_run(
            self.db, job.agent_run_id, status="queued", completed_at=None, failure_reason=None
        )
        await agent_state.log_run_event(
            self.db, job.agent_run_id, "retry_manually_triggered", {"job_id": str(job_id)}
        )

        # Delete any dead letter records associated
        stmt_dlq = delete(AgentExecutionDeadLetter).where(AgentExecutionDeadLetter.job_id == job_id)
        await self.db.execute(stmt_dlq)

        # Delete any existing leases
        stmt_lease = delete(AgentExecutionLease).where(AgentExecutionLease.job_id == job_id)
        await self.db.execute(stmt_lease)

        await self.db.commit()
        await update_queue_metrics(self.db, job.tenant_id, job.agent_id)
        logger.info(f"Manually triggered retry for job {job_id}")
        return True
