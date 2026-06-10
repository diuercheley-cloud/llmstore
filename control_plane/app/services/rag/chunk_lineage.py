from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...models.commercial.commercial_rag_vault import (
    CommercialRAGChunk,
    CommercialRAGDocument,
    CommercialRAGVault,
)


async def get_chunk_lineage(db: AsyncSession, chunk_hash: str) -> Optional[dict]:
    res = await db.execute(
        select(CommercialRAGChunk, CommercialRAGDocument, CommercialRAGVault)
        .join(CommercialRAGDocument, CommercialRAGChunk.document_id == CommercialRAGDocument.id)
        .join(CommercialRAGVault, CommercialRAGDocument.vault_id == CommercialRAGVault.id)
        .where(CommercialRAGChunk.chunk_hash == chunk_hash)
    )
    
    row = res.one_or_none()
    if not row:
        return None
        
    chunk, doc, vault = row
    
    return {
        "chunk_hash": chunk.chunk_hash,
        "chunk_index": chunk.chunk_index,
        "document_hash": doc.document_hash,
        "classification": doc.classification_level,
        "vault_id": str(vault.id),
        "tenant_id": vault.tenant_id,
        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None
    }
