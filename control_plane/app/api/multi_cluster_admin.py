# Owner: platform-ops
from typing import Any, List, Optional

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.services.multi_cluster_operations import MultiClusterOperationsService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/clusters", tags=["multi_cluster"])

class ClusterCreate(BaseModel):
    name: str
    cluster_type: str
    base_url: str
    location: Optional[str] = None

class ClusterResponse(BaseModel):
    id: str
    name: str
    cluster_type: str
    status: str
    base_url: str
    location: Optional[str] = None

@router.post("", response_model=ClusterResponse)
async def create_cluster(
    data: ClusterCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.create_cluster(data.name, data.cluster_type, data.base_url, data.location)

@router.get("", response_model=List[ClusterResponse])
async def list_clusters(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.list_clusters()

@router.get("/status")
async def get_multi_cluster_status(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    clusters = await service.list_clusters()
    return {"status": "operational", "clusters": clusters}

@router.get("/{id}")
async def get_cluster(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    cluster = await service.get_cluster(id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster

@router.post("/{id}/maintenance")
async def put_in_maintenance(
    id: str,
    reason: str = "Scheduled maintenance",
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.set_cluster_status(id, "maintenance", reason=reason, operator_id=admin.id)

@router.post("/{id}/drain")
async def drain_cluster(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.set_cluster_status(id, "degraded", reason="Draining traffic", operator_id=admin.id)

@router.post("/{id}/resume")
async def resume_cluster(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.set_cluster_status(id, "active", reason="Resuming normal operations", operator_id=admin.id)

@router.get("/{id}/sync-events")
async def list_sync_events(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = MultiClusterOperationsService(db)
    return await service.list_sync_events(id)
