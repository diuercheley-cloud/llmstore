import hashlib
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...models.commercial.commercial_merkle_timelines import CommercialMerkleTimeline
from ...models.commercial.commercial_transparency import (
    CommercialConsistencyCheckpoint,
    CommercialTransparencyGossipPeer,
    CommercialTransparencyGossipRecord,
    CommercialTransparencySplitViewAlert,
)


async def create_consistency_checkpoint(
    db: AsyncSession,
    checkpoint_type: str,
    period_start: datetime,
    period_end: datetime
) -> CommercialConsistencyCheckpoint:
    # 1. Aggregate roots/hashes for the period
    if checkpoint_type == "merkle_timeline":
        result = await db.execute(
            select(CommercialMerkleTimeline).where(
                CommercialMerkleTimeline.created_at >= period_start,
                CommercialMerkleTimeline.created_at <= period_end
            )
        )
        timelines = result.scalars().all()
        roots = [t.merkle_root for t in timelines]
        combined_payload = ":".join(sorted(roots))
        root_hash = hashlib.sha256(combined_payload.encode()).hexdigest()
    else:
        # Simplified for other types in this phase
        root_hash = hashlib.sha256(f"{checkpoint_type}:{period_start}:{period_end}".encode()).hexdigest()

    checkpoint = CommercialConsistencyCheckpoint(
        checkpoint_type=checkpoint_type,
        period_start=period_start,
        period_end=period_end,
        root_hash=root_hash,
        witness_summary_json={"timeline_count": 0} # Placeholder
    )
    db.add(checkpoint)
    await db.commit()
    await db.refresh(checkpoint)
    return checkpoint

async def export_checkpoint(checkpoint: CommercialConsistencyCheckpoint) -> dict:
    return {
        "id": str(checkpoint.id),
        "checkpoint_type": checkpoint.checkpoint_type,
        "period_start": checkpoint.period_start.isoformat(),
        "period_end": checkpoint.period_end.isoformat(),
        "root_hash": checkpoint.root_hash,
        "signed_checkpoint": checkpoint.signed_checkpoint,
        "witness_summary": checkpoint.witness_summary_json,
        "created_at": checkpoint.created_at.isoformat()
    }

async def ingest_checkpoint(db: AsyncSession, payload: dict) -> CommercialConsistencyCheckpoint:
    checkpoint = CommercialConsistencyCheckpoint(
        checkpoint_type=payload["checkpoint_type"],
        period_start=datetime.fromisoformat(payload["period_start"]),
        period_end=datetime.fromisoformat(payload["period_end"]),
        root_hash=payload["root_hash"],
        signed_checkpoint=payload.get("signed_checkpoint"),
        witness_summary_json=payload.get("witness_summary", {})
    )
    db.add(checkpoint)
    await db.commit()
    await db.refresh(checkpoint)
    
    # Trigger consistency check automatically
    await detect_split_view(db, checkpoint)
    return checkpoint

async def compare_checkpoints(
    db: AsyncSession,
    checkpoint_id_a: uuid.UUID,
    checkpoint_id_b: uuid.UUID
) -> dict:
    res_a = await db.execute(select(CommercialConsistencyCheckpoint).where(CommercialConsistencyCheckpoint.id == checkpoint_id_a))
    cp_a = res_a.scalar_one_or_none()
    res_b = await db.execute(select(CommercialConsistencyCheckpoint).where(CommercialConsistencyCheckpoint.id == checkpoint_id_b))
    cp_b = res_b.scalar_one_or_none()
    
    if not cp_a or not cp_b:
        return {"status": "error", "message": "One or both checkpoints not found"}
        
    is_consistent = cp_a.root_hash == cp_b.root_hash
    return {
        "is_consistent": is_consistent,
        "root_hash_a": cp_a.root_hash,
        "root_hash_b": cp_b.root_hash,
        "period_match": cp_a.period_start == cp_b.period_start and cp_a.period_end == cp_b.period_end
    }

async def detect_split_view(db: AsyncSession, new_checkpoint: CommercialConsistencyCheckpoint):
    # Check if there is another checkpoint for the same period with a different hash
    result = await db.execute(
        select(CommercialConsistencyCheckpoint).where(
            CommercialConsistencyCheckpoint.checkpoint_type == new_checkpoint.checkpoint_type,
            CommercialConsistencyCheckpoint.period_start == new_checkpoint.period_start,
            CommercialConsistencyCheckpoint.period_end == new_checkpoint.period_end,
            CommercialConsistencyCheckpoint.root_hash != new_checkpoint.root_hash,
            CommercialConsistencyCheckpoint.id != new_checkpoint.id
        )
    )
    conflict = result.scalar_one_or_none()
    
    if conflict:
        alert = CommercialTransparencySplitViewAlert(
            alert_type="checkpoint_conflict",
            severity="critical",
            expected_hash=conflict.root_hash,
            observed_hash=new_checkpoint.root_hash,
            summary=f"Divergent checkpoint detected for {new_checkpoint.checkpoint_type} in period {new_checkpoint.period_start} to {new_checkpoint.period_end}"
        )
        db.add(alert)
        await db.commit()
        return alert
    return None

async def gossip_with_peer(db: AsyncSession, peer_id: str, payload: dict) -> CommercialTransparencyGossipRecord:
    # Record the gossip event
    record = CommercialTransparencyGossipRecord(
        source_peer_id=peer_id,
        timeline_root=payload.get("timeline_root"),
        checkpoint_hash=payload.get("checkpoint_hash"),
        gossip_type=payload.get("gossip_type", "manual"),
        verification_status="unknown"
    )
    
    # If we have a local checkpoint for comparison
    if record.checkpoint_hash:
        result = await db.execute(
            select(CommercialConsistencyCheckpoint).where(
                CommercialConsistencyCheckpoint.root_hash == record.checkpoint_hash
            )
        )
        local = result.scalar_one_or_none()
        if local:
            record.verification_status = "valid"
        else:
            # Maybe check if we have a checkpoint for the same period but different hash
            # This logic depends on more metadata being gossiped
            pass

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record

async def summarize_transparency_status(db: AsyncSession) -> dict:
    peers_res = await db.execute(select(CommercialTransparencyGossipPeer))
    peers = peers_res.scalars().all()
    
    alerts_res = await db.execute(select(CommercialTransparencySplitViewAlert).where(CommercialTransparencySplitViewAlert.resolved == False))
    alerts = alerts_res.scalars().all()
    
    return {
        "total_peers": len(peers),
        "active_alerts": len(alerts),
        "status": "compromised" if any(a.severity == "critical" for a in alerts) else "healthy"
    }
