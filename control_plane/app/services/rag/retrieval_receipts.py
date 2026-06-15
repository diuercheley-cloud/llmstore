import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.commercial.commercial_rag_vault import CommercialRetrievalReceipt


async def generate_retrieval_receipt(
    db: AsyncSession,
    vault_id: uuid.UUID,
    session_id: str,
    query_text: str,
    retrieved_chunk_hashes: list[str],
) -> CommercialRetrievalReceipt:
    query_hash = hashlib.sha256(query_text.encode()).hexdigest()

    # Hash of everything to form the receipt
    payload = f"{vault_id}:{session_id}:{query_hash}:{','.join(retrieved_chunk_hashes)}"
    receipt_hash = hashlib.sha256(payload.encode()).hexdigest()

    receipt = CommercialRetrievalReceipt(
        vault_id=vault_id,
        session_id=session_id,
        query_hash=query_hash,
        retrieved_chunk_hashes=retrieved_chunk_hashes,
        receipt_hash=receipt_hash,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return receipt
