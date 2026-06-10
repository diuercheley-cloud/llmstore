import uuid
from typing import Any, Dict, List, Optional

from app.db.session import get_db_session
from app.models.core.federation_mesh import FederationPeer
from app.services.federation.mesh.mesh_sync import MeshSyncService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/federation", tags=["admin-federation-mesh"])


@router.get("/peers")
async def list_peers(db: AsyncSession = Depends(get_db_session)):
    stmt = select(FederationPeer)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/sync/export")
async def export_sync_bundle(
    since_hash: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    # In a real system, node_id would come from config
    service = MeshSyncService(db, node_id="local-cluster-01")
    bundle = await service.export_bundle(since_hash=since_hash)
    return bundle


@router.post("/sync/import")
async def import_sync_bundle(
    bundle: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session)
):
    service = MeshSyncService(db, node_id="local-cluster-01")
    try:
        results = await service.import_bundle(bundle)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/dry-run")
async def dry_run_sync_bundle(
    bundle: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session)
):
    service = MeshSyncService(db, node_id="local-cluster-01")
    try:
        results = await service.import_bundle(bundle, dry_run=True)
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
