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
from sqlalchemy import select, delete
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
)

logger = logging.getLogger(__name__)

class AgentWorkerService:
    def __init__(self, worker_id: str | None = None):
        self.settings = get_settings()
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self._heartbeat_task = None

    async def register_heartbeat(self, db: AsyncSession) -> None:
        now = utc_now()
        stmt = select(AgentWorkerHeartbeat).where(AgentWorkerHeartbeat.worker_id == self.worker_id)
        res = await db.execute(stmt)
        hb = res.scalar_one_or_none()

        if hb:
            hb.last_heartbeat = now
            hb.status = "active"
        else:
            hb = AgentWorkerHeartbeat(
                worker_id=self.worker_id,
                last_heartbeat=now,
                status="active",
                started_at=now,
            )
            db.add(hb)

        LLM_AGENT_WORKER_HEARTBEATS_TOTAL.labels(worker_id=self.worker_id).inc()
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

        # Register initial heartbeat
        async with SessionLocal() as db:
            await self.register_heartbeat(db)

        # Start heartbeat background loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Mark worker as inactive in database
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

    async def run_once(self) -> bool:
        """
        Polls and executes a single job.
        Returns True if a job was executed, False if the queue was empty.
        """
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
        
        # Start lease renewer loop
        lease_renewer = asyncio.create_task(self._lease_renewer_loop(job_id))

        try:
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

            else:
                # Handle unexpected/failed step executions (retry, backoff or dead letter)
                await self._handle_job_failure(job_id, failure_reason)

        except Exception as e:
            logger.exception(f"Unexpected error executing job {job_id}")
            lease_renewer.cancel()
            await self._handle_job_failure(job_id, str(e))

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
