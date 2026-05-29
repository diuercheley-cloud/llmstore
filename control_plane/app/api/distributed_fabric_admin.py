# Owner: platform-ops
# Owner: platform-ops
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.api.dependencies.auth import get_current_admin
from sqlalchemy import select
from app.models.runtime.distributed_runtime import RuntimeCluster, RuntimeNode, DistributedAgentJob
import uuid

router = APIRouter(prefix="/admin/distributed-runtime", tags=["distributed_runtime_admin"])

@router.get("/clusters")
async def list_clusters(db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    result = await db.execute(select(RuntimeCluster))
    return list(result.scalars().all())

@router.post("/clusters")
async def register_cluster(name: str, region: str, is_managed: bool = False, db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    cluster = RuntimeCluster(name=name, region=region, is_managed=is_managed)
    db.add(cluster)
    await db.commit()
    await db.refresh(cluster)
    return cluster

@router.get("/nodes")
async def list_nodes(db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    result = await db.execute(select(RuntimeNode))
    return list(result.scalars().all())

@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    result = await db.execute(select(DistributedAgentJob))
    return list(result.scalars().all())

@router.post("/jobs/{job_id}/failover")
async def failover_job(job_id: uuid.UUID, to_node_id: uuid.UUID, reason: str = "manual", db: AsyncSession = Depends(get_db_session), admin=Depends(get_current_admin)):
    from app.models.runtime.distributed_runtime import DistributedFailoverEvent
    
    result = await db.execute(select(DistributedAgentJob).where(DistributedAgentJob.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from_node_id = job.target_node_id
    job.target_node_id = to_node_id
    
    event = DistributedFailoverEvent(
        job_id=job_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        reason=reason
    )
    db.add(event)
    await db.commit()
    return event
