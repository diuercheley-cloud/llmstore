# Owner: commercial-ops
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_admin_user
from ..db.session import get_db
from ..models.commercial_rag_vault import (
    CommercialRetrievalPolicyViolation,
    CommercialRetrievalReceipt,
)
from ..services.rag import chunk_lineage

router = APIRouter(prefix="/admin/rag", tags=["Confidential RAG Vault Admin"])

@router.get("/receipts", response_model=List[dict])
async def list_receipts(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialRetrievalReceipt).order_by(CommercialRetrievalReceipt.created_at.desc()).limit(100))
    receipts = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "vault_id": str(r.vault_id),
            "session_id": r.session_id,
            "receipt_hash": r.receipt_hash,
            "created_at": r.created_at.isoformat()
        }
        for r in receipts
    ]

@router.get("/violations", response_model=List[dict])
async def list_violations(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialRetrievalPolicyViolation).order_by(CommercialRetrievalPolicyViolation.created_at.desc()).limit(100))
    violations = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "session_id": v.session_id,
            "violation_type": v.violation_type,
            "action_taken": v.action_taken,
            "created_at": v.created_at.isoformat()
        }
        for v in violations
    ]

@router.get("/lineage/{chunk_hash}")
async def get_lineage(chunk_hash: str, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    lineage = await chunk_lineage.get_chunk_lineage(db, chunk_hash)
    if not lineage:
        raise HTTPException(status_code=404, detail="Chunk lineage not found")
    return lineage
