# Owner: commercial-ops
"""Admin API for Verifiable AI Execution Proofs + Merkle Audit Timelines.

Provides endpoints to build, seal, verify, and export Merkle timelines
and execution proofs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.commercial.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.models.commercial.commercial_merkle_timelines import (
    CommercialExecutionProof,
    CommercialMerkleLeaf,
    CommercialMerkleTimeline,
)
from app.services.inference.execution_proofs import (
    build_receipt_timeline,
    build_replay_timeline,
    build_runtime_integrity_timeline,
    export_execution_proof,
    generate_execution_proof,
    verify_execution_proof,
)
from app.services.inference.merkle_timelines import (
    MerkleError,
    seal_timeline,
    validate_timeline_chain,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/inference/proofs", tags=["admin", "execution-proofs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings():
    return get_settings()


# ---------------------------------------------------------------------------
# Timeline endpoints
# ---------------------------------------------------------------------------

@router.get("/timelines", dependencies=[Depends(require_admin)])
async def list_timelines(
    db: AsyncSession = Depends(get_db),
    timeline_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List Merkle timelines with optional filters."""
    stmt = select(CommercialMerkleTimeline)
    if timeline_type:
        stmt = stmt.where(CommercialMerkleTimeline.timeline_type == timeline_type)
    if status:
        stmt = stmt.where(CommercialMerkleTimeline.status == status)
    stmt = stmt.order_by(CommercialMerkleTimeline.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(t.id),
                "timeline_type": t.timeline_type,
                "period_start": t.period_start.isoformat() if t.period_start else None,
                "period_end": t.period_end.isoformat() if t.period_end else None,
                "leaf_count": t.leaf_count,
                "merkle_root": t.merkle_root,
                "previous_timeline_root": t.previous_timeline_root,
                "status": t.status,
                "sealed_at": t.sealed_at.isoformat() if t.sealed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.post("/timelines/build", dependencies=[Depends(require_admin)])
async def build_timeline(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Build a new Merkle timeline for the requested type and window."""
    body = await request.json()
    timeline_type = body.get("timeline_type", "inference_receipts")
    minutes = body.get("window_minutes", _settings().commercial_merkle_timeline_window_minutes)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)

    builders = {
        "inference_receipts": build_receipt_timeline,
        "runtime_integrity": build_runtime_integrity_timeline,
        "replay_events": build_replay_timeline,
    }
    builder = builders.get(timeline_type)
    if not builder:
        raise HTTPException(status_code=400, detail="Invalid timeline type")

    timeline = await builder(db, start, end)
    db.add(timeline)
    await db.commit()
    await db.refresh(timeline)

    return {
        "id": str(timeline.id),
        "timeline_type": timeline.timeline_type,
        "period_start": timeline.period_start.isoformat(),
        "period_end": timeline.period_end.isoformat(),
        "leaf_count": timeline.leaf_count,
        "merkle_root": timeline.merkle_root,
        "previous_timeline_root": timeline.previous_timeline_root,
        "status": timeline.status,
        "created_at": timeline.created_at.isoformat(),
    }


@router.post("/timelines/{timeline_id}/seal", dependencies=[Depends(require_admin)])
async def seal_timeline_endpoint(
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Seal a timeline, making it immutable and computing its final root."""
    timeline = (await db.execute(
        select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.id == timeline_id)
    )).scalar_one_or_none()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    if timeline.status == "sealed":
        raise HTTPException(status_code=400, detail="Timeline already sealed")

    leaves = (await db.execute(
        select(CommercialMerkleLeaf).where(CommercialMerkleLeaf.timeline_id == timeline_id).order_by(
            CommercialMerkleLeaf.leaf_index
        )
    )).scalars().all()
    leaf_hashes = [leaf.leaf_hash for leaf in leaves]

    try:
        root = seal_timeline(leaf_hashes, timeline.previous_timeline_root)
    except MerkleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    timeline.merkle_root = root
    timeline.status = "sealed"
    timeline.sealed_at = datetime.now(timezone.utc)
    timeline.timeline_hash = root  # update with the sealed root
    await db.commit()
    await db.refresh(timeline)
    return {
        "id": str(timeline.id),
        "status": timeline.status,
        "merkle_root": timeline.merkle_root,
        "sealed_at": timeline.sealed_at.isoformat(),
    }


@router.post("/timelines/{timeline_id}/verify", dependencies=[Depends(require_admin)])
async def verify_timeline_endpoint(
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Verify a timeline's chain integrity and detect tampering."""
    timeline = (await db.execute(
        select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.id == timeline_id)
    )).scalar_one_or_none()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")

    leaves = (await db.execute(
        select(CommercialMerkleLeaf).where(CommercialMerkleLeaf.timeline_id == timeline_id).order_by(
            CommercialMerkleLeaf.leaf_index
        )
    )).scalars().all()
    leaf_hashes = [leaf.leaf_hash for leaf in leaves]

    valid = validate_timeline_chain(
        timeline.merkle_root,
        timeline.previous_timeline_root,
        timeline.timeline_hash,
    )

    return {
        "id": str(timeline.id),
        "valid": valid,
        "leaf_count": len(leaves),
        "status": timeline.status,
    }


# ---------------------------------------------------------------------------
# Proof endpoints
# ---------------------------------------------------------------------------

@router.get("/proofs", dependencies=[Depends(require_admin)])
async def list_proofs(
    db: AsyncSession = Depends(get_db),
    proof_type: str | None = Query(None),
    verification_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List execution proofs with optional filters."""
    stmt = select(CommercialExecutionProof)
    if proof_type:
        stmt = stmt.where(CommercialExecutionProof.proof_type == proof_type)
    if verification_status:
        stmt = stmt.where(CommercialExecutionProof.verification_status == verification_status)
    stmt = stmt.order_by(CommercialExecutionProof.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(p.id),
                "receipt_id": str(p.receipt_id) if p.receipt_id else None,
                "timeline_id": str(p.timeline_id),
                "proof_type": p.proof_type,
                "proof_hash": p.proof_hash,
                "verification_status": p.verification_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.post("/proofs/generate/{receipt_id}", dependencies=[Depends(require_admin)])
async def generate_proof_endpoint(
    receipt_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate an execution proof for a given receipt."""
    receipt = (await db.execute(
        select(CommercialInferenceReceipt).where(CommercialInferenceReceipt.id == receipt_id)
    )).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Find or build a timeline for this receipt
    timeline = (await db.execute(
        select(CommercialMerkleTimeline)
        .where(CommercialMerkleTimeline.timeline_type == "inference_receipts")
        .where(CommercialMerkleTimeline.status == "sealed")
        .order_by(CommercialMerkleTimeline.created_at.desc())
    )).scalars().first()
    if not timeline:
        raise HTTPException(status_code=400, detail="No sealed timeline available")

    leaves = (await db.execute(
        select(CommercialMerkleLeaf).where(CommercialMerkleLeaf.timeline_id == timeline.id).order_by(
            CommercialMerkleLeaf.leaf_index
        )
    )).scalars().all()

    proof = await generate_execution_proof(db, timeline, receipt, leaves)
    db.add(proof)
    await db.commit()
    await db.refresh(proof)

    return {
        "id": str(proof.id),
        "proof_hash": proof.proof_hash,
        "verification_status": proof.verification_status,
        "created_at": proof.created_at.isoformat(),
    }


@router.post("/proofs/{proof_id}/verify", dependencies=[Depends(require_admin)])
async def verify_proof_endpoint(
    proof_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Verify an execution proof."""
    proof = (await db.execute(
        select(CommercialExecutionProof).where(CommercialExecutionProof.id == proof_id)
    )).scalar_one_or_none()
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")

    valid = await verify_execution_proof(db, proof)
    proof.verification_status = "valid" if valid else "invalid"
    proof.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(proof)

    return {
        "id": str(proof.id),
        "valid": valid,
        "verification_status": proof.verification_status,
        "verified_at": proof.verified_at.isoformat(),
    }


@router.get("/proofs/{proof_id}/export", dependencies=[Depends(require_admin)])
async def export_proof_endpoint(
    proof_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Export a tenant-safe execution proof."""
    proof = (await db.execute(
        select(CommercialExecutionProof).where(CommercialExecutionProof.id == proof_id)
    )).scalar_one_or_none()
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")

    exported = await export_execution_proof(proof)
    return exported
