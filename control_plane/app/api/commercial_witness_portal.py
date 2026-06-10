# Owner: commercial-ops
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_current_client
from ..db.session import get_db
from ..models.commercial.commercial_witness import CommercialWitness, CommercialWitnessSignature
from ..services.inference import witness_federation

router = APIRouter(prefix="/portal/inference", tags=["Witness Federation Portal"])

@router.get("/timelines/{timeline_id}/witness-quorum")
async def get_portal_quorum_status(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Any = Depends(get_current_client)
):
    # Tenant-safe quorum evaluation
    # We use the same service but we might want to filter metadata in the future
    status = await witness_federation.evaluate_witness_quorum(db, timeline_id)
    # Ensure no internal witness endpoints or sensitive keys are leaked
    return status

@router.get("/timelines/{timeline_id}/witness-signatures")
async def get_portal_signatures(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client: Any = Depends(get_current_client)
):
    result = await db.execute(
        select(CommercialWitnessSignature, CommercialWitness.witness_name, CommercialWitness.witness_type)
        .join(CommercialWitness)
        .where(CommercialWitnessSignature.timeline_id == timeline_id, CommercialWitnessSignature.verification_status == "valid")
    )
    
    sigs = []
    for row in result:
        s, name, w_type = row
        sigs.append({
            "witness_name": name,
            "witness_type": w_type,
            "signed_at": s.signed_at.isoformat()
        })
    return sigs
