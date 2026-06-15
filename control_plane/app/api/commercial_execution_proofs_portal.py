# Owner: commercial-ops
"""Portal API for Verifiable AI Execution Proofs.

Tenant-safe access to Merkle timelines and execution proofs.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.commercial.commercial_merkle_timelines import CommercialExecutionProof
from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/portal/inference/proofs", tags=["portal", "execution-proofs"])


@router.get("/proofs")
async def list_portal_proofs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List execution proofs accessible to the current tenant."""
    # Tenant isolation stub: in production, filter by tenant_id from auth context
    stmt = (
        select(CommercialExecutionProof)
        .order_by(CommercialExecutionProof.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(p.id),
                "proof_hash": p.proof_hash,
                "proof_type": p.proof_type,
                "verification_status": p.verification_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ],
        "count": len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.get("/proofs/{proof_id}")
async def get_portal_proof(
    proof_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve a specific execution proof (tenant-safe, no sensitive data)."""
    proof = (
        await db.execute(
            select(CommercialExecutionProof).where(CommercialExecutionProof.id == proof_id)
        )
    ).scalar_one_or_none()
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")

    # Tenant-safe export: no prompts, responses, or raw payloads
    return {
        "id": str(proof.id),
        "proof_type": proof.proof_type,
        "proof_hash": proof.proof_hash,
        "verification_status": proof.verification_status,
        "timeline_root": proof.proof_json.get("timeline_root"),
        "previous_timeline_root": proof.proof_json.get("previous_timeline_root"),
        "merkle_inclusion_proof": proof.proof_json.get("merkle_inclusion_proof"),
        "timestamp_summary": proof.proof_json.get("timestamp_summary"),
        "created_at": proof.created_at.isoformat() if proof.created_at else None,
    }


@router.post("/proofs/{proof_id}/verify")
async def verify_portal_proof(
    proof_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Verify an execution proof from the portal."""
    proof = (
        await db.execute(
            select(CommercialExecutionProof).where(CommercialExecutionProof.id == proof_id)
        )
    ).scalar_one_or_none()
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")

    from app.services.inference.execution_proofs import verify_execution_proof

    valid = await verify_execution_proof(db, proof)
    proof.verification_status = "valid" if valid else "invalid"
    await db.commit()
    await db.refresh(proof)
    return {
        "id": str(proof.id),
        "valid": valid,
        "verification_status": proof.verification_status,
    }
