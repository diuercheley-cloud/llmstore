"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_execution import (
    AgentExecutionJob,
    AgentExecutionLease,
    AgentExecutionRetry,
    AgentExecutionDeadLetter,
)
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents import agent_state
from app.core.metrics import (
    LLM_AGENT_JOBS_QUEUED,
    LLM_AGENT_JOBS_RUNNING,
    LLM_AGENT_JOBS_FAILED_TOTAL,
    LLM_AGENT_JOB_RETRIES_TOTAL,
    LLM_AGENT_DEAD_LETTERS_TOTAL,
    LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL,
)

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ["queued", "leased", "running", "waiting_approval"]

class BackpressureError(Exception):
    def __init__(self, message: str, limit_type: str):
        super().__init__(message)
        self.limit_type = limit_type


async def update_queue_metrics(db: AsyncSession, tenant_id: str, agent_id: uuid.UUID):
    try:
        # Queued count
        stmt_q = select(func.count(AgentExecutionJob.id)).where(
            AgentExecutionJob.tenant_id == tenant_id,
            AgentExecutionJob.agent_id == agent_id,
            AgentExecutionJob.status == "queued"
        )
        res_q = await db.execute(stmt_q)
        queued_count = res_q.scalar_one()
        LLM_AGENT_JOBS_QUEUED.labels(tenant_id=tenant_id, agent_id=str(agent_id)).set(queued_count)

        # Running/leased count
        stmt_r = select(func.count(AgentExecutionJob.id)).where(
            AgentExecutionJob.tenant_id == tenant_id,
            AgentExecutionJob.agent_id == agent_id,
            AgentExecutionJob.status.in_(["leased", "running", "waiting_approval"])
        )
        res_r = await db.execute(stmt_r)
        running_count = res_r.scalar_one()
        LLM_AGENT_JOBS_RUNNING.labels(tenant_id=tenant_id, agent_id=str(agent_id)).set(running_count)
    except Exception as e:
        logger.error(f"Failed to update queue metrics: {e}")


class AgentQueueManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def enqueue_job(
        self,
        agent_run_id: uuid.UUID,
        agent_id: uuid.UUID,
        tenant_id: str,
        max_attempts: int = 3,
        initial_delay_seconds: int = 5,
        backoff_factor: float = 2.0,
    ) -> AgentExecutionJob:
        if not self.settings.agent_execution_plane_enabled:
            raise RuntimeError("Agent Execution Plane is disabled.")

        # Multi-tier Backpressure check
        if self.settings.agent_queue_backpressure_enabled:
            # 1. Global queue depth limit (max 100)
            stmt_global = select(func.count(AgentExecutionJob.id)).where(
                AgentExecutionJob.status.in_(ACTIVE_STATUSES)
            )
            res_global = await self.db.execute(stmt_global)
            global_count = res_global.scalar_one()
            if global_count >= 100:
                LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL.labels(
                    tenant_id=tenant_id, agent_id=str(agent_id), limit_type="global"
                ).inc()
                raise BackpressureError("Global queue depth limit exceeded (max 100)", "global")

            # 2. Tenant concurrency limit (max 10)
            stmt_tenant = select(func.count(AgentExecutionJob.id)).where(
                AgentExecutionJob.tenant_id == tenant_id,
                AgentExecutionJob.status.in_(ACTIVE_STATUSES)
            )
            res_tenant = await self.db.execute(stmt_tenant)
            tenant_count = res_tenant.scalar_one()
            if tenant_count >= 10:
                LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL.labels(
                    tenant_id=tenant_id, agent_id=str(agent_id), limit_type="tenant"
                ).inc()
                raise BackpressureError("Tenant concurrent limit exceeded (max 10)", "tenant")

            # 3. Agent concurrency limit (max 5)
            stmt_agent = select(func.count(AgentExecutionJob.id)).where(
                AgentExecutionJob.agent_id == agent_id,
                AgentExecutionJob.status.in_(ACTIVE_STATUSES)
            )
            res_agent = await self.db.execute(stmt_agent)
            agent_count = res_agent.scalar_one()
            if agent_count >= 5:
                LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL.labels(
                    tenant_id=tenant_id, agent_id=str(agent_id), limit_type="agent"
                ).inc()
                raise BackpressureError("Agent concurrent limit exceeded (max 5)", "agent")

            # 4. Risk level limit (low: 50, medium: 10, high: 3, critical: 1)
            stmt_def = select(AgentDefinition.risk_level).where(AgentDefinition.id == agent_id)
            res_def = await self.db.execute(stmt_def)
            risk_level = res_def.scalar_one_or_none() or "low"

            risk_limit = {"low": 50, "medium": 10, "high": 3, "critical": 1}.get(risk_level, 50)
            stmt_risk = select(func.count(AgentExecutionJob.id)).join(
                AgentDefinition, AgentExecutionJob.agent_id == AgentDefinition.id
            ).where(
                AgentExecutionJob.status.in_(ACTIVE_STATUSES),
                AgentDefinition.risk_level == risk_level
            )
            res_risk = await self.db.execute(stmt_risk)
            risk_count = res_risk.scalar_one()
            if risk_count >= risk_limit:
                LLM_AGENT_QUEUE_BACKPRESSURE_TOTAL.labels(
                    tenant_id=tenant_id, agent_id=str(agent_id), limit_type=f"risk_level_{risk_level}"
                ).inc()
                raise BackpressureError(
                    f"Risk level '{risk_level}' limit exceeded (max {risk_limit})", f"risk_level_{risk_level}"
                )

        # Create execution job
        job = AgentExecutionJob(
            agent_run_id=agent_run_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            status="queued",
            attempts=0,
            max_attempts=max_attempts,
            backoff_factor=backoff_factor,
            initial_delay_seconds=initial_delay_seconds,
            scheduled_at=utc_now(),
        )
        self.db.add(job)
        await self.db.flush()

        await agent_state.log_run_event(
            self.db, agent_run_id, "enqueued", {"job_id": str(job.id)}
        )

        await self.db.commit()
        await update_queue_metrics(self.db, tenant_id, agent_id)
        logger.info(f"Enqueued job {job.id} for run {agent_run_id} (tenant: {tenant_id})")
        return job

    async def dequeue_job(self, worker_id: str, lease_timeout_seconds: int = 60) -> AgentExecutionJob | None:
        if not self.settings.agent_execution_plane_enabled:
            return None

        # Reclaim any expired leases first
        await self.reclaim_expired_leases()

        # Find next queued job that is scheduled to run
        now = utc_now()
        stmt = (
            select(AgentExecutionJob)
            .where(
                AgentExecutionJob.status == "queued",
                AgentExecutionJob.scheduled_at <= now
            )
            .order_by(AgentExecutionJob.scheduled_at.asc())
            .with_for_update(skip_locked=True)
        )
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            return None

        # Atomically lease the job
        job.status = "leased"
        job.updated_at = now

        # Create lease
        lease = AgentExecutionLease(
            job_id=job.id,
            worker_id=worker_id,
            leased_at=now,
            expires_at=now + timedelta(seconds=lease_timeout_seconds),
        )
        self.db.add(lease)
        
        await agent_state.log_run_event(
            self.db, job.agent_run_id, "leased", {"worker_id": worker_id}
        )

        await self.db.commit()
        await update_queue_metrics(self.db, job.tenant_id, job.agent_id)
        logger.info(f"Worker {worker_id} leased job {job.id} until {lease.expires_at}")
        return job

    async def reclaim_expired_leases(self) -> None:
        now = utc_now()
        # Find all expired leases
        stmt_leases = (
            select(AgentExecutionLease)
            .where(AgentExecutionLease.expires_at <= now)
            .with_for_update()
        )
        res_leases = await self.db.execute(stmt_leases)
        expired_leases = res_leases.scalars().all()

        for lease in expired_leases:
            # Load corresponding job
            stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == lease.job_id).with_for_update()
            res_job = await self.db.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            
            if not job:
                # Job no longer exists, just remove lease
                await self.db.delete(lease)
                continue

            if job.status in ("completed", "failed", "cancelled"):
                # Job has finished, just delete lease
                await self.db.delete(lease)
                continue

            # Increment attempts and check limits
            job.attempts += 1
            error_msg = f"Lease expired. Worker {lease.worker_id} failed to renew heartbeat."
            
            # Record retry attempt
            retry_record = AgentExecutionRetry(
                job_id=job.id,
                attempt=job.attempts,
                error_message=error_msg,
                attempted_at=now,
                next_attempt_at=now # calculated below
            )

            if job.attempts < job.max_attempts:
                # Calculate backoff delay
                delay = job.initial_delay_seconds * (job.backoff_factor ** (job.attempts - 1))
                next_attempt = now + timedelta(seconds=delay)
                retry_record.next_attempt_at = next_attempt

                job.status = "queued"
                job.scheduled_at = next_attempt
                job.updated_at = now

                await agent_state.log_run_event(
                    self.db, job.agent_run_id, "retry_scheduled", {
                        "attempt": job.attempts,
                        "next_attempt_at": next_attempt.isoformat(),
                        "reason": "lease_expired"
                    }
                )
                LLM_AGENT_JOB_RETRIES_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                logger.warn(f"Job {job.id} lease expired. Re-enqueued for attempt {job.attempts + 1} at {next_attempt}")
            else:
                # Max attempts reached, move to DLQ
                job.status = "dead_letter"
                job.updated_at = now

                dlq = AgentExecutionDeadLetter(
                    job_id=job.id,
                    agent_run_id=job.agent_run_id,
                    agent_id=job.agent_id,
                    tenant_id=job.tenant_id,
                    last_error=error_msg,
                    failed_at=now,
                )
                self.db.add(dlq)

                # Set associated run to failed
                await agent_state.update_run(
                    self.db, job.agent_run_id, status="failed", failure_reason="Max execution attempts reached", completed_at=now
                )
                await agent_state.log_run_event(
                    self.db, job.agent_run_id, "dead_letter", {"reason": error_msg}
                )

                LLM_AGENT_JOBS_FAILED_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                LLM_AGENT_DEAD_LETTERS_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                logger.error(f"Job {job.id} lease expired and exceeded max attempts ({job.max_attempts}). Moved to DLQ.")

            self.db.add(retry_record)
            await self.db.delete(lease)
            await self.db.flush()
            await update_queue_metrics(self.db, job.tenant_id, job.agent_id)

        if expired_leases:
            await self.db.commit()
