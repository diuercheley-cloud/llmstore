# Owner: agent-platform
import uuid
from typing import Any, Dict, List

from app.api.deps import get_db_session, require_admin
from app.core.time import utc_now
from app.models.agent_execution import AgentExecutionDeadLetter, AgentExecutionJob
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/worker", tags=["agent-worker-admin"])

@router.get("/dlq")
async def list_dlq(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    stmt = select(AgentExecutionDeadLetter).order_by(AgentExecutionDeadLetter.failed_at.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [
        {
            "id": str(item.id),
            "job_id": str(item.job_id),
            "agent_run_id": str(item.agent_run_id),
            "tenant_id": item.tenant_id,
            "last_error": item.last_error,
            "failed_at": item.failed_at.isoformat()
        }
        for item in items
    ]

@router.post("/dlq/{dlq_id}/retry")
async def retry_dlq_item(
    dlq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    stmt = select(AgentExecutionDeadLetter).where(AgentExecutionDeadLetter.id == dlq_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="DLQ item not found")

    # Requeue job
    stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.id == item.job_id)
    res_job = await db.execute(stmt_job)
    job = res_job.scalar_one_or_none()
    if job:
        job.queue_status = "queued"
        job.attempt_count = 0
        job.available_at = utc_now()
        job.updated_at = utc_now()
        
        # Also need to reset run status
        from app.services.agents import agent_state
        await agent_state.update_run(db, job.agent_run_id, status="queued")

    await db.delete(item)
    await db.commit()
    return {"status": "requeued", "job_id": str(item.job_id)}

@router.delete("/dlq/{dlq_id}")
async def purge_dlq_item(
    dlq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    stmt = delete(AgentExecutionDeadLetter).where(AgentExecutionDeadLetter.id == dlq_id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "deleted"}
