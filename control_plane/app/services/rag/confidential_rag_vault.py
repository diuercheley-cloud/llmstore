import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...models.commercial_rag_vault import (
    CommercialRAGChunk,
    CommercialRAGDocument,
    CommercialRAGVault,
    CommercialRetrievalPolicyViolation,
)


async def create_vault(
    db: AsyncSession,
    tenant_id: str,
    vault_name: str,
    retention_days: int = 30
) -> CommercialRAGVault:
    vault = CommercialRAGVault(
        tenant_id=tenant_id,
        vault_name=vault_name,
        retention_policy_days=retention_days,
        encryption_key_hash=hashlib.sha256(tenant_id.encode()).hexdigest()
    )
    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    return vault

async def add_document_to_vault(
    db: AsyncSession,
    vault_id: uuid.UUID,
    content: str,
    classification: str = "confidential"
) -> CommercialRAGDocument:
    doc_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Check vault retention
    res = await db.execute(select(CommercialRAGVault).where(CommercialRAGVault.id == vault_id))
    vault = res.scalar_one()
    expires_at = datetime.utcnow() + timedelta(days=vault.retention_policy_days)
    
    doc = CommercialRAGDocument(
        vault_id=vault_id,
        document_hash=doc_hash,
        classification_level=classification,
        expires_at=expires_at
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # Add a mock chunk for testing
    chunk_hash = hashlib.sha256((content + "_chunk0").encode()).hexdigest()
    chunk = CommercialRAGChunk(
        document_id=doc.id,
        chunk_hash=chunk_hash,
        chunk_index=0
    )
    db.add(chunk)
    await db.commit()
    
    return doc

async def log_policy_violation(
    db: AsyncSession,
    vault_id: uuid.UUID,
    session_id: str,
    query_hash: str,
    violation_type: str
) -> CommercialRetrievalPolicyViolation:
    violation = CommercialRetrievalPolicyViolation(
        vault_id=vault_id,
        session_id=session_id,
        query_hash=query_hash,
        violation_type=violation_type
    )
    db.add(violation)
    await db.commit()
    await db.refresh(violation)
    return violation
