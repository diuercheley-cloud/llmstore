# Owner: platform-ops
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_db, get_current_admin
from app.services.gpu_orchestrator import GpuOrchestrator
from app.models.runtime.gpu_orchestration import GpuDevice, GpuAllocation, AutoscalingPolicy, AutoscalingEvent
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["gpu_autoscaling"])

class AutoscalingPolicyCreate(BaseModel):
    model_registry_id: uuid.UUID
    name: str
    strategy: str = "queue_depth"
    min_replicas: int = 1
    max_replicas: int = 5
    target_value: float
    cooldown_seconds: int = 300
    is_active: bool = True
    mode: str = "recommendation"

@router.get("/gpu/devices")
async def list_gpu_devices(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(GpuDevice))
    return result.scalars().all()

@router.get("/gpu/capacity/{node_id}")
async def get_gpu_capacity(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    orchestrator = GpuOrchestrator(db)
    return await orchestrator.get_node_gpu_capacity(node_id)

@router.get("/gpu/allocations")
async def list_gpu_allocations(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(GpuAllocation))
    return result.scalars().all()

@router.get("/autoscaling/policies")
async def list_autoscaling_policies(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(AutoscalingPolicy))
    return result.scalars().all()

@router.post("/autoscaling/policies")
async def create_autoscaling_policy(
    policy_data: AutoscalingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    policy = AutoscalingPolicy(**policy_data.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

@router.get("/autoscaling/events")
async def list_autoscaling_events(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    result = await db.execute(select(AutoscalingEvent).order_by(AutoscalingEvent.created_at.desc()))
    return result.scalars().all()
