"""
Owner: agent-platform
Status: beta
"""
import logging
import uuid

from app.core.metrics import LLM_AGENT_JOBS_CANCELLED_TOTAL
from app.core.time import utc_now
from app.models.agent_execution import AgentExecutionJob, AgentExecutionLease
from app.models.agents import AgentRun
from app.services.agents import agent_state
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AgentCancellationService:
    @staticmethod
    async def cancel_job(db: AsyncSession, job_id: uuid.UUID) -> bool:
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return False

        if job.queue_status == "cancelled":
            return True

        # Transition status
        job.queue_status = "cancelled"
        job.updated_at = utc_now()

        # Update the associated AgentRun status to "cancelled"
        await agent_state.update_run(db, job.agent_run_id, status="cancelled", completed_at=utc_now())
        await agent_state.log_run_event(db, job.agent_run_id, "cancelled", {"reason": "admin_request"})

        # Record metrics
        LLM_AGENT_JOBS_CANCELLED_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()

        # Delete any leases
        stmt_delete = delete(AgentExecutionLease).where(AgentExecutionLease.job_id == job.id)
        await db.execute(stmt_delete)

        await db.commit()
        logger.info(f"Successfully cancelled job {job_id} and deleted associated leases.")
        return True

    @staticmethod
    async def cancel_run(db: AsyncSession, run_id: uuid.UUID) -> bool:
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            return await AgentCancellationService.cancel_job(db, job.id)
        
        # If no job exists, update run directly
        run = await agent_state.get_agent_run(db, run_id)
        if run and run.status != "cancelled":
            await agent_state.update_run(db, run_id, status="cancelled", completed_at=utc_now())
            await agent_state.log_run_event(db, run_id, "cancelled", {"reason": "admin_request"})
            await db.commit()
            return True
        return False

    @staticmethod
    async def is_cancelled(db: AsyncSession, run_id: uuid.UUID) -> bool:
        # Refresh from DB to bypass session cache
        stmt = select(AgentRun.status).where(AgentRun.id == run_id)
        res = await db.execute(stmt)
        status = res.scalar_one_or_none()
        return status == "cancelled"
