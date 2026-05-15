import uuid
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..db.session import get_db
from ..models.commercial_rag_vault import (
    CommercialRAGVault,
    CommercialRAGDocument,
    CommercialRAGChunk,
    CommercialRetrievalReceipt,
    CommercialRetrievalPolicyViolation
)
from ..services.rag import confidential_rag_vault, retrieval_receipts, chunk_lineage
from ..api.dependencies import get_admin_user

router = APIRouter(prefix="/admin/rag", tags=["Confidential RAG Vault Admin"])

@router.get("/vaults", response_model=List[dict])
async def list_vaults(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialRAGVault).order_by(CommercialRAGVault.created_at.desc()))
    vaults = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "tenant_id": v.tenant_id,
            "vault_name": v.vault_name,
            "is_encrypted": v.is_encrypted,
            "retention_policy_days": v.retention_policy_days,
            "created_at": v.created_at.isoformat()
        }
        for v in vaults
    ]

@router.post("/vaults")
async def create_vault(payload: dict, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    vault = await confidential_rag_vault.create_vault(
        db, 
        tenant_id=payload["tenant_id"],
        vault_name=payload["vault_name"],
        retention_days=payload.get("retention_days", 30)
    )
    return {"id": str(vault.id), "vault_name": vault.vault_name}

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
