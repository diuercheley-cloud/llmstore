# Owner: agent-platform
import uuid
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.core.time import utc_now
from app.models.agents.agent_execution import AgentExecutionJob, AgentWorkerHeartbeat
from app.services.agents import agent_state
from app.services.agents.agent_cancellation import AgentCancellationService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/execution", tags=["agent-execution-admin"])


@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    stmt = select(AgentExecutionJob).order_by(AgentExecutionJob.created_at.desc())
    res = await db.execute(stmt)
    jobs = res.scalars().all()
    return [
        {
            "id": str(job.id),
            "agent_run_id": str(job.agent_run_id),
            "agent_id": str(job.agent_id),
            "tenant_id": job.tenant_id,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "scheduled_at": job.scheduled_at.isoformat(),
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
        for job in jobs
    ]


@router.get("/workers")
async def list_workers(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> list[dict[str, Any]]:
    stmt = select(AgentWorkerHeartbeat).order_by(AgentWorkerHeartbeat.last_heartbeat.desc())
    res = await db.execute(stmt)
    workers = res.scalars().all()
    return [
        {
            "worker_id": worker.worker_id,
            "status": worker.status,
            "last_heartbeat": worker.last_heartbeat.isoformat(),
            "started_at": worker.started_at.isoformat(),
        }
        for worker in workers
    ]


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Execution job not found")

    await AgentCancellationService.cancel_run(db, job.agent_run_id)

    job.queue_status = "cancelled"
    job.updated_at = utc_now()
    await db.commit()

    run = await agent_state.get_agent_run(db, job.agent_run_id)
    return {
        "status": "cancelled",
        "job_id": str(job.id),
        "run_id": str(job.agent_run_id),
        "run_status": run.status if run else "cancelled",
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Execution job not found")

    job.queue_status = "queued"
    job.available_at = utc_now()
    job.updated_at = utc_now()

    run = await agent_state.get_agent_run(db, job.agent_run_id)
    if run is not None:
        await agent_state.update_run(
            db,
            job.agent_run_id,
            status="queued",
            completed_at=None,
            failure_reason=None,
        )

    await db.commit()
    return {
        "status": "retrying",
        "job_id": str(job.id),
        "run_id": str(job.agent_run_id),
    }
