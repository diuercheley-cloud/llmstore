"""
Owner: agent-platform
Status: beta
"""
import asyncio
import uuid
import logging
import traceback
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.agent_execution import (
    AgentExecutionJob,
    AgentWorkerHeartbeat,
    AgentExecutionLease,
    AgentExecutionRetry,
    AgentExecutionDeadLetter,
)
from app.models.agents import AgentRun
from app.services.agents.agent_executor import AgentExecutor
from app.services.agents.agent_cancellation import AgentCancellationService
from app.services.agents.agent_queue import AgentQueueManager, update_queue_metrics
from app.services.agents import agent_state
from app.core.metrics import (
    LLM_AGENT_JOBS_COMPLETED_TOTAL,
    LLM_AGENT_JOBS_FAILED_TOTAL,
    LLM_AGENT_JOBS_CANCELLED_TOTAL,
    LLM_AGENT_JOB_RETRIES_TOTAL,
    LLM_AGENT_DEAD_LETTERS_TOTAL,
    LLM_AGENT_WORKER_HEARTBEATS_TOTAL,
    LLM_AGENT_ACTIVE_LEASES,
    LLM_AGENT_DRAIN_STATUS,
    LLM_AGENT_ACTIVE_WORKERS,
    LLM_AGENT_STUCK_RUNS_TOTAL
)

logger = logging.getLogger(__name__)

class AgentWorkerService:
    def __init__(self, worker_id: str | None = None):
        self.settings = get_settings()
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.is_draining = False
        self._heartbeat_task = None
        self._recovery_task = None

    async def register_heartbeat(self, db: AsyncSession) -> None:
        now = utc_now()
        stmt = select(AgentWorkerHeartbeat).where(AgentWorkerHeartbeat.worker_id == self.worker_id)
        res = await db.execute(stmt)
        hb = res.scalar_one_or_none()

        status = "draining" if self.is_draining else "active"
        if hb:
            hb.last_heartbeat = now
            hb.status = status
        else:
            hb = AgentWorkerHeartbeat(
                worker_id=self.worker_id,
                last_heartbeat=now,
                status=status,
                started_at=now,
            )
            db.add(hb)

        # Count globally active workers for metrics
        stmt_count = select(func.count(AgentWorkerHeartbeat.worker_id)).where(
            AgentWorkerHeartbeat.last_heartbeat >= now - timedelta(minutes=2),
            AgentWorkerHeartbeat.status != "inactive"
        )
        res_count = await db.execute(stmt_count)
        active_count = res_count.scalar() or 0
        from app.core.metrics import LLM_AGENT_ACTIVE_WORKERS
        LLM_AGENT_ACTIVE_WORKERS.set(active_count)

        LLM_AGENT_WORKER_HEARTBEATS_TOTAL.labels(worker_id=self.worker_id).inc()
        LLM_AGENT_DRAIN_STATUS.labels(worker_id=self.worker_id).set(1 if self.is_draining else 0)
        await db.commit()

    async def start(self) -> None:
        if not self.settings.agent_execution_plane_enabled:
            logger.warning("Agent Execution Plane is disabled. Worker will not start.")
            return

        if not self.settings.agent_worker_enabled:
            logger.warning("Agent Worker is disabled. Worker will not start.")
            return

        self.is_running = True
        logger.info(f"Starting Agent Worker: {self.worker_id}")

        async with SessionLocal() as db:
            await self.register_heartbeat(db)

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._recovery_task = asyncio.create_task(self._recovery_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._recovery_task:
            self._recovery_task.cancel()
        
        # Mark worker as inactive
        try:
            async with SessionLocal() as db:
                stmt = select(AgentWorkerHeartbeat).where(AgentWorkerHeartbeat.worker_id == self.worker_id)
                res = await db.execute(stmt)
                hb = res.scalar_one_or_none()
                if hb:
                    hb.status = "inactive"
                    hb.last_heartbeat = utc_now()
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to record inactive status for worker {self.worker_id}: {e}")

        logger.info(f"Stopped Agent Worker: {self.worker_id}")

    def drain(self) -> None:
        """Sets the worker to drain mode: finishes current job then stops."""
        logger.info(f"Worker {self.worker_id} entering DRAIN mode.")
        self.is_draining = True

    async def _heartbeat_loop(self) -> None:
        while self.is_running:
            try:
                await asyncio.sleep(10)
                async with SessionLocal() as db:
                    await self.register_heartbeat(db)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _recovery_loop(self) -> None:
        """Background loop to recover orphan leases and stuck runs globally."""
        while self.is_running:
            try:
                await asyncio.sleep(60) # Run every minute
                async with SessionLocal() as db:
                    await self.recover_orphans(db)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")

    async def recover_orphans(self, db: AsyncSession) -> int:
        """Identifies expired leases and puts jobs back in queue. Also identifies stuck runs."""
        now = utc_now()
        
        # 1. Recover orphan leases
        stmt = select(AgentExecutionLease).where(AgentExecutionLease.expires_at <= now)
        res = await db.execute(stmt)
        expired = res.scalars().all()
        
        count = 0
        for lease in expired:
            stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == lease.job_id).with_for_update()
            res_job = await db.execute(stmt_job)
            job = res_job.scalar_one_or_none()
            if job and job.status == "running":
                logger.warning(f"Recovering orphan job {job.id} from expired lease.")
                job.status = "queued"
                job.updated_at = now
                count += 1
            
            await db.delete(lease)
        
        # 2. Monitor stuck runs (running for > 2 hours with no recent update)
        stmt_stuck = select(func.count(AgentRun.id)).where(
            AgentRun.status == "running",
            AgentRun.updated_at <= now - timedelta(hours=2)
        )
        res_stuck = await db.execute(stmt_stuck)
        stuck_count = res_stuck.scalar() or 0
        LLM_AGENT_STUCK_RUNS_TOTAL.set(stuck_count)
        
        if count > 0:
            await db.commit()
            logger.info(f"Recovered {count} orphan leases.")
        return count

    async def run_once(self) -> bool:
        if self.is_draining:
            logger.info(f"Worker {self.worker_id} is draining. Skipping pickup.")
            return False

        async with SessionLocal() as db:
            queue_mgr = AgentQueueManager(db)
            job = await queue_mgr.dequeue_job(self.worker_id, lease_timeout_seconds=60)
            if not job:
                return False

            job_id = job.id
            run_id = job.agent_run_id
            tenant_id = job.tenant_id
            agent_id = job.agent_id

        # Execute the job
        logger.info(f"Worker {self.worker_id} executing job {job_id} for run {run_id}")
        LLM_AGENT_ACTIVE_LEASES.inc()
        
        lease_renewer = asyncio.create_task(self._lease_renewer_loop(job_id))

        try:
            # ... (rest of implementation remains similar)
            async with SessionLocal() as db:
                # Transition job status to running
                stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id).with_for_update()
                res = await db.execute(stmt)
                db_job = res.scalar_one()
                db_job.status = "running"
                db_job.updated_at = utc_now()
                
                # Check run status, set to running if currently queued
                run = await agent_state.get_agent_run(db, run_id)
                if run and run.status == "queued":
                    await agent_state.update_run(db, run_id, status="running")

                await db.commit()

            # Execute run steps
            execution_failed = False
            failure_reason = None
            
            while True:
                # Check cancellation first
                async with SessionLocal() as db:
                    cancelled = await AgentCancellationService.is_cancelled(db, run_id)
                    if cancelled:
                        logger.info(f"Run {run_id} has been cancelled. Stopping execution.")
                        async with SessionLocal() as db_cancel:
                            stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id).with_for_update()
                            res_job = await db_cancel.execute(stmt_job)
                            j = res_job.scalar_one()
                            j.status = "cancelled"
                            j.updated_at = utc_now()
                            await delete_lease_by_job_id(db_cancel, job_id)
                            await db_cancel.commit()
                            await update_queue_metrics(db_cancel, tenant_id, agent_id)
                        LLM_AGENT_JOBS_CANCELLED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()
                        break

                # Execute step
                try:
                    async with SessionLocal() as db_step:
                        executor = AgentExecutor(db_step, run_id)
                        should_continue = await executor.execute_step()
                        
                        # We must commit steps & changes
                        await db_step.commit()
                except Exception as step_exc:
                    logger.exception(f"Step execution threw exception for run {run_id}")
                    execution_failed = True
                    failure_reason = str(step_exc)
                    break

                if not should_continue:
                    break

            # Handle execution completion / terminal states
            lease_renewer.cancel()
            
            if not execution_failed:
                async with SessionLocal() as db:
                    # Check run's final status
                    run = await agent_state.get_agent_run(db, run_id)
                    stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id).with_for_update()
                    res_job = await db.execute(stmt_job)
                    db_job = res_job.scalar_one()

                    if run:
                        if run.status == "completed":
                            db_job.status = "completed"
                            LLM_AGENT_JOBS_COMPLETED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()
                        elif run.status == "failed":
                            db_job.status = "failed"
                            LLM_AGENT_JOBS_FAILED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()
                        elif run.status == "cancelled":
                            db_job.status = "cancelled"
                            LLM_AGENT_JOBS_CANCELLED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()
                        elif run.status == "waiting_approval":
                            db_job.status = "waiting_approval"
                        else:
                            db_job.status = "completed"  # fallback
                            LLM_AGENT_JOBS_COMPLETED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()
                    else:
                        db_job.status = "completed"
                        LLM_AGENT_JOBS_COMPLETED_TOTAL.labels(tenant_id=tenant_id, agent_id=str(agent_id)).inc()

                    db_job.updated_at = utc_now()
                    await delete_lease_by_job_id(db, job_id)
                    await db.commit()
                    await update_queue_metrics(db, tenant_id, agent_id)
                    logger.info(f"Finished job {job_id} with status {db_job.status}")
                LLM_AGENT_ACTIVE_LEASES.dec()

            else:
                # Handle unexpected/failed step executions (retry, backoff or dead letter)
                await self._handle_job_failure(job_id, failure_reason)
                LLM_AGENT_ACTIVE_LEASES.dec()

        except Exception as e:
            logger.exception(f"Unexpected error executing job {job_id}")
            lease_renewer.cancel()
            await self._handle_job_failure(job_id, str(e))
            LLM_AGENT_ACTIVE_LEASES.dec()

        return True

    async def _lease_renewer_loop(self, job_id: uuid.UUID) -> None:
        while True:
            try:
                await asyncio.sleep(15)
                async with SessionLocal() as db:
                    stmt = select(AgentExecutionLease).where(AgentExecutionLease.job_id == job_id).with_for_update()
                    res = await db.execute(stmt)
                    lease = res.scalar_one_or_none()
                    if lease:
                        lease.expires_at = utc_now() + timedelta(seconds=60)
                        await db.commit()
                        logger.debug(f"Renewed lease for job {job_id} until {lease.expires_at}")
                    else:
                        logger.warning(f"Lease not found for job {job_id} during renewal")
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error renewing lease for job {job_id}: {e}")

    async def _handle_job_failure(self, job_id: uuid.UUID, error_message: str) -> None:
        now = utc_now()
        async with SessionLocal() as db:
            stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id).with_for_update()
            res_job = await db.execute(stmt_job)
            job = res_job.scalar_one_or_none()

            if not job:
                return

            job.attempts += 1
            
            # Record retry record
            retry_record = AgentExecutionRetry(
                job_id=job.id,
                attempt=job.attempts,
                error_message=error_message,
                attempted_at=now,
                next_attempt_at=now
            )

            if job.attempts < job.max_attempts:
                delay = job.initial_delay_seconds * (job.backoff_factor ** (job.attempts - 1))
                next_attempt = now + timedelta(seconds=delay)
                retry_record.next_attempt_at = next_attempt

                job.status = "queued"
                job.scheduled_at = next_attempt
                job.updated_at = now

                # Also update run status to queued so worker picks it up
                await agent_state.update_run(
                    db, job.agent_run_id, status="queued"
                )
                await agent_state.log_run_event(
                    db, job.agent_run_id, "retry_scheduled", {
                        "attempt": job.attempts,
                        "next_attempt_at": next_attempt.isoformat(),
                        "reason": error_message
                    }
                )
                LLM_AGENT_JOB_RETRIES_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                logger.warn(f"Job {job_id} failed. Re-enqueued for attempt {job.attempts + 1} at {next_attempt}. Error: {error_message}")
            else:
                job.status = "dead_letter"
                job.updated_at = now

                dlq = AgentExecutionDeadLetter(
                    job_id=job.id,
                    agent_run_id=job.agent_run_id,
                    agent_id=job.agent_id,
                    tenant_id=job.tenant_id,
                    last_error=error_message,
                    failed_at=now,
                )
                db.add(dlq)

                await agent_state.update_run(
                    db, job.agent_run_id, status="failed", failure_reason=f"Execution failed after {job.max_attempts} attempts: {error_message}", completed_at=now
                )
                await agent_state.log_run_event(
                    db, job.agent_run_id, "dead_letter", {"reason": error_message}
                )

                LLM_AGENT_JOBS_FAILED_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                LLM_AGENT_DEAD_LETTERS_TOTAL.labels(tenant_id=job.tenant_id, agent_id=str(job.agent_id)).inc()
                logger.error(f"Job {job_id} exceeded max attempts ({job.max_attempts}) and moved to DLQ. Error: {error_message}")

            db.add(retry_record)
            await delete_lease_by_job_id(db, job_id)
            await db.commit()
            await update_queue_metrics(db, job.tenant_id, job.agent_id)


async def delete_lease_by_job_id(db: AsyncSession, job_id: uuid.UUID) -> None:
    stmt = delete(AgentExecutionLease).where(AgentExecutionLease.job_id == job_id)
    await db.execute(stmt)
