# Owner: commercial-ops
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_admin_user
from ..db.session import get_db
from ..models.commercial_transparency import (
    CommercialConsistencyCheckpoint,
    CommercialTransparencyGossipPeer,
    CommercialTransparencySplitViewAlert,
)
from ..services.inference import transparency_gossip

router = APIRouter(prefix="/admin/inference/transparency", tags=["Transparency Gossip"])

@router.get("/peers", response_model=List[dict])
async def list_peers(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialTransparencyGossipPeer))
    peers = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "peer_id": p.peer_id,
            "peer_type": p.peer_type,
            "status": p.status,
            "endpoint": p.endpoint,
            "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None
        }
        for p in peers
    ]

@router.post("/peers")
async def create_peer(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    peer = CommercialTransparencyGossipPeer(
        peer_id=payload["peer_id"],
        peer_type=payload["peer_type"],
        endpoint=payload.get("endpoint"),
        public_key=payload.get("public_key"),
        metadata_json=payload.get("metadata", {})
    )
    db.add(peer)
    await db.commit()
    await db.refresh(peer)
    return {"id": str(peer.id), "status": "created"}

@router.get("/checkpoints", response_model=List[dict])
async def list_checkpoints(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialConsistencyCheckpoint).order_by(CommercialConsistencyCheckpoint.created_at.desc()))
    checkpoints = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "checkpoint_type": c.checkpoint_type,
            "period_start": c.period_start.isoformat(),
            "period_end": c.period_end.isoformat(),
            "root_hash": c.root_hash,
            "created_at": c.created_at.isoformat()
        }
        for c in checkpoints
    ]

@router.post("/checkpoints")
async def create_checkpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    checkpoint = await transparency_gossip.create_consistency_checkpoint(
        db,
        checkpoint_type=payload["checkpoint_type"],
        period_start=datetime.fromisoformat(payload["period_start"]),
        period_end=datetime.fromisoformat(payload["period_end"])
    )
    return {"id": str(checkpoint.id), "root_hash": checkpoint.root_hash}

@router.post("/gossip")
async def process_gossip(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    peer_id = payload.get("peer_id", "anonymous")
    record = await transparency_gossip.gossip_with_peer(db, peer_id, payload)
    return {"id": str(record.id), "verification_status": record.verification_status}

@router.post("/ingest-checkpoint")
async def ingest_checkpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    checkpoint = await transparency_gossip.ingest_checkpoint(db, payload)
    return {"id": str(checkpoint.id), "status": "ingested"}

@router.get("/split-view-alerts", response_model=List[dict])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialTransparencySplitViewAlert).order_by(CommercialTransparencySplitViewAlert.created_at.desc()))
    alerts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "severity": a.severity,
            "summary": a.summary,
            "resolved": a.resolved,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

@router.post("/split-view-alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialTransparencySplitViewAlert).where(CommercialTransparencySplitViewAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.resolved = True
    alert.resolved_at = datetime.now(UTC)
    await db.commit()
    return {"status": "resolved"}

@router.get("/status")
async def get_transparency_status(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    return await transparency_gossip.summarize_transparency_status(db)
