# Owner: agent-platform
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.agents.federated_memory.memory_summary_sync import MemorySummarySync
from app.services.agents.federated_memory.remote_memory_reference import RemoteMemoryReferenceService
from app.models.agent_federated_memory import FederatedMemoryPeer

router = APIRouter(prefix="/admin/agents/federated-memory", tags=["Federated Memory"])

@router.post("/peers")
async def register_peer(
    config: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    peer = FederatedMemoryPeer(
        cluster_id=config["cluster_id"],
        cluster_name=config["name"],
        endpoint_url=config["endpoint"],
        trust_level=config.get("trust_level", "standard"),
        data_residency_region=config["region"]
    )
    db.add(peer)
    await db.commit()
    await db.refresh(peer)
    return peer

@router.post("/sync/summary")
async def sync_memory_summary(
    peer_id: uuid.UUID,
    tenant_id: str,
    summary: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    service = MemorySummarySync(db)
    try:
        return await service.sync_summary(peer_id, tenant_id, summary)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/revoke")
async def propagate_revocation(
    cluster_id: str,
    memory_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = RemoteMemoryReferenceService(db)
    count = await service.revoke_reference(cluster_id, memory_id)
    return {"status": "revoked", "invalidated_references": count}
