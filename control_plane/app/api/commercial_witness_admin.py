# Owner: commercial-ops
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.deps import get_admin_user
from ..db.session import get_db
from ..models.commercial.commercial_witness import (
    CommercialWitness,
    CommercialWitnessSignature,
)
from ..services.inference import witness_federation

router = APIRouter(prefix="/admin/inference", tags=["Witness Federation"])

@router.get("/witnesses", response_model=List[dict])
async def list_witnesses(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialWitness))
    witnesses = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "witness_name": w.witness_name,
            "witness_type": w.witness_type,
            "status": w.status,
            "trust_level": w.trust_level,
            "endpoint": w.endpoint,
            "public_key": w.public_key,
            "created_at": w.created_at.isoformat()
        }
        for w in witnesses
    ]

@router.post("/witnesses")
async def create_witness(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    witness = await witness_federation.register_witness(
        db,
        name=payload["witness_name"],
        witness_type=payload["witness_type"],
        public_key=payload.get("public_key"),
        endpoint=payload.get("endpoint"),
        trust_level=payload.get("trust_level", "medium"),
        metadata=payload.get("metadata", {})
    )
    return {"id": str(witness.id), "status": "registered"}

@router.patch("/witnesses/{witness_id}")
async def update_witness(
    witness_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    result = await db.execute(select(CommercialWitness).where(CommercialWitness.id == witness_id))
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")
        
    for key, value in payload.items():
        if hasattr(witness, key):
            setattr(witness, key, value)
            
    await db.commit()
    return {"status": "updated"}

@router.post("/witnesses/{witness_id}/verify")
async def verify_witness_connectivity(
    witness_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    # Simulated connectivity check
    result = await db.execute(select(CommercialWitness).where(CommercialWitness.id == witness_id))
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")
        
    is_online = witness.status != "offline"
    return {"online": is_online, "latency_ms": 120 if is_online else None}

@router.get("/witness-signatures", response_model=List[dict])
async def list_signatures(
    timeline_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    query = select(CommercialWitnessSignature)
    if timeline_id:
        query = query.where(CommercialWitnessSignature.timeline_id == timeline_id)
    
    result = await db.execute(query)
    sigs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "timeline_id": str(s.timeline_id),
            "witness_id": str(s.witness_id),
            "verification_status": s.verification_status,
            "signed_at": s.signed_at.isoformat()
        }
        for s in sigs
    ]

@router.post("/timelines/{timeline_id}/witness-sign")
async def sign_timeline(
    timeline_id: uuid.UUID,
    witness_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    sig = await witness_federation.request_witness_signature(db, timeline_id, witness_id)
    if not sig:
        raise HTTPException(status_code=400, detail="Signature request failed")
    return {"id": str(sig.id), "status": sig.verification_status}

@router.get("/timelines/{timeline_id}/witness-quorum")
async def get_quorum_status(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    return await witness_federation.evaluate_witness_quorum(db, timeline_id)

@router.get("/witness-status")
async def get_federation_summary(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user)
):
    return await witness_federation.summarize_witness_status(db)
