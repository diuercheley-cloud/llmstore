# Owner: platform-ops
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_admin
from app.services.runtime.distributed_runtime import DistributedRuntimeService
from pydantic import BaseModel

router = APIRouter(prefix="/runtime/nodes", tags=["distributed_runtime"])

class NodeRegisterSchema(BaseModel):
    name: str
    base_url: str
    node_type: str = "remote"
    gpu_count: int = 0
    gpu_memory_total_mb: int = 0
    cpu_count: int = 0
    memory_total_mb: int = 0
    capabilities: dict = {}
    trust_level: int = 1

class NodeHeartbeatSchema(BaseModel):
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: dict = {}
    active_requests: int = 0
    metrics: dict = {}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_node(
    node_data: NodeRegisterSchema,
    db: AsyncSession = Depends(get_db)
):
    service = DistributedRuntimeService(db)
    node = await service.register_node(node_data.model_dump())
    return node

@router.post("/{node_id}/heartbeat")
async def record_heartbeat(
    node_id: uuid.UUID,
    heartbeat_data: NodeHeartbeatSchema,
    db: AsyncSession = Depends(get_db)
):
    service = DistributedRuntimeService(db)
    await service.record_heartbeat(node_id, heartbeat_data.model_dump())
    return {"status": "ok"}

@router.post("/{node_id}/drain")
async def drain_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    service = DistributedRuntimeService(db)
    await service.drain_node(node_id)
    return {"status": "draining"}

@router.get("/")
async def list_nodes(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    service = DistributedRuntimeService(db)
    nodes = await service.list_nodes(status)
    return nodes

@router.get("/{node_id}")
async def get_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    service = DistributedRuntimeService(db)
    node = await service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node
