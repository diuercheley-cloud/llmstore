import uuid
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...models.commercial.commercial_rag_vault import CommercialRAGDocument, CommercialRAGVault
from .confidential_rag_vault import log_policy_violation


async def sanitize_retrieval(
    db: AsyncSession,
    vault_id: uuid.UUID,
    session_id: str,
    query_hash: str,
    retrieved_documents: List[CommercialRAGDocument],
    tenant_id: str
) -> Tuple[List[CommercialRAGDocument], List[str]]:
    # Verify tenant
    res = await db.execute(select(CommercialRAGVault).where(CommercialRAGVault.id == vault_id))
    vault = res.scalar_one_or_none()
    
    if not vault or vault.tenant_id != tenant_id:
        await log_policy_violation(db, vault_id, session_id, query_hash, "cross_tenant")
        return [], ["cross_tenant_blocked"]
        
    safe_docs = []
    blocks = []
    
    for doc in retrieved_documents:
        if doc.classification_level == "restricted":
            blocks.append(f"blocked_restricted_doc:{doc.document_hash}")
            await log_policy_violation(db, vault_id, session_id, query_hash, "classification_mismatch")
        else:
            safe_docs.append(doc)
            
    return safe_docs, blocks
