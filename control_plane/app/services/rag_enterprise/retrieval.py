import uuid
import logging
from typing import List, Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.core.config import get_settings
from app.services.rag_enterprise.schemas import EnterpriseSource, EnterpriseQueryResponse
from app.services.rag_enterprise.embeddings import get_enterprise_embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    a_arr = np.array(a)
    b_arr = np.array(b)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


async def search_chunks(
    session: AsyncSession,
    client_id: uuid.UUID,
    query_embedding: List[float],
    top_k: int = 5,
    score_threshold: float = 0.0,
    document_ids: Optional[List[uuid.UUID]] = None,
    collection_ids: Optional[List[uuid.UUID]] = None,
) -> List[Tuple[float, RAGDocumentChunk, Optional[RAGDocument]]]:
    stmt = select(RAGDocumentChunk).where(RAGDocumentChunk.client_id == client_id)

    if document_ids:
        stmt = stmt.where(RAGDocumentChunk.document_id.in_(document_ids))

    chunks = (await session.execute(stmt)).scalars().all()

    if not chunks:
        return []

    doc_cache: dict[uuid.UUID, Optional[RAGDocument]] = {}

    scored_chunks = []
    for chunk in chunks:
        if chunk.embedding is None:
            continue
        score = cosine_similarity(query_embedding, chunk.embedding)
        if score < score_threshold:
            continue

        doc_id = chunk.document_id
        if doc_id not in doc_cache:
            doc_result = await session.execute(
                select(RAGDocument).where(RAGDocument.id == doc_id)
            )
            doc_cache[doc_id] = doc_result.scalar_one_or_none()

        doc = doc_cache.get(doc_id)
        if doc is None:
            continue

        scored_chunks.append((score, chunk, doc))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return scored_chunks[:top_k]


async def execute_enterprise_query(
    session: AsyncSession,
    client_id: uuid.UUID,
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    document_ids: Optional[List[uuid.UUID]] = None,
    collection_ids: Optional[List[uuid.UUID]] = None,
    cloud_allowed: bool = False,
) -> Tuple[List[EnterpriseSource], List[float]]:
    embedding_service = get_enterprise_embedding_service()
    query_embedding = await embedding_service.embed_text(question, cloud_allowed=cloud_allowed)

    scored_results = await search_chunks(
        session=session,
        client_id=client_id,
        query_embedding=query_embedding,
        top_k=top_k,
        score_threshold=score_threshold,
        document_ids=document_ids,
        collection_ids=collection_ids,
    )

    sources = []
    all_scores = []
    for score, chunk, doc in scored_results:
        page = chunk.page_number or 0
        sources.append(EnterpriseSource(
            document_id=chunk.document_id,
            filename=doc.original_filename if doc else "unknown",
            page=page,
            chunk_index=chunk.chunk_index,
            text=chunk.content,
            score=float(score),
        ))
        all_scores.append(float(score))

    return sources, all_scores


def build_rag_context(sources: List[EnterpriseSource]) -> str:
    parts = []
    for src in sources:
        parts.append(
            f"[fonte: {src.filename}"
            f"{', página ' + str(src.page) if src.page else ''}"
            f"]\n{src.text}\n"
        )
    return "\n".join(parts)
