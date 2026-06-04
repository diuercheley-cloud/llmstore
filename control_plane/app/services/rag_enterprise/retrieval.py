import logging
import re
import uuid
from typing import Any, List, Optional, Tuple

import numpy as np
from app.core.config import get_settings
from app.models.commercial_encryption import CommercialEncryptedArtifact
from app.models.commercial_rag_vault import (
    CommercialRAGChunk,
    CommercialRAGDocument,
    CommercialRAGVault,
)
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.services.rag.rag_access_control import (
    evaluate_chunk_acl,
    evaluate_retrieval_access,
    validate_document_access,
)
from app.services.rag.rag_audit import hash_payload
from app.services.rag.rag_poison_detection import analyze_and_record_poisoning
from app.services.rag.rag_vault import (
    sanitize_chunk_preview,
    sanitize_text,
)
from app.services.rag_enterprise.embeddings import get_enterprise_embedding_service
from app.services.rag_enterprise.schemas import EnterpriseSource
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    from app.services.vectorstores.vectorstore_factory import VectorStoreFactory
    store = VectorStoreFactory.get_instance(session=session)
    
    filters = {"client_id": client_id}
    if document_ids:
        # Simple implementation: use the first document_id if provided
        filters["document_id"] = document_ids[0]

    hits = await store.search(
        collection_name="rag_chunks",
        vector=query_embedding,
        limit=top_k,
        filters=filters
    )

    if not hits:
        return []

    results = []
    doc_cache: dict[uuid.UUID, Optional[RAGDocument]] = {}

    for hit in hits:
        if hit.get("score", 0.0) < score_threshold:
            continue
            
        chunk_id = uuid.UUID(hit["id"])
        chunk = (await session.execute(
            select(RAGDocumentChunk).where(RAGDocumentChunk.id == chunk_id)
        )).scalar_one_or_none()
        
        if not chunk:
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

        results.append((float(hit["score"]), chunk, doc))

    return results


async def execute_enterprise_query(
    session: AsyncSession,
    client_id: uuid.UUID,
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    document_ids: Optional[List[uuid.UUID]] = None,
    collection_ids: Optional[List[uuid.UUID]] = None,
    cloud_allowed: bool = False,
    user_identity: Optional[str] = None,
    requested_model: Optional[str] = None,
    abac_attributes: Optional[dict[str, Any]] = None,
    return_audit: bool = False,
) -> Tuple[List[EnterpriseSource], List[float]] | Tuple[List[EnterpriseSource], List[float], dict[str, Any]]:
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
    audit_payload: dict[str, Any] = {
        "governed": False,
        "policy_result": "allow",
        "violations": [],
        "sanitized": True,
        "retrieval_hash": None,
    }

    vault = None
    access_context = None
    commercial_chunk_ids: list[str] = []
    if settings.commercial_rag_vault_enabled:
        vault = (
            await session.execute(
                select(CommercialRAGVault).where(CommercialRAGVault.client_id == client_id)
            )
        ).scalar_one_or_none()
        if vault:
            access_context = await evaluate_retrieval_access(
                session,
                vault=vault,
                request_client_id=client_id,
                requested_model=requested_model,
                user_identity=user_identity,
                abac_attributes=abac_attributes,
            )
            audit_payload["governed"] = True
            audit_payload["max_context_chunks"] = access_context.max_context_chunks

    for score, chunk, doc in scored_results:
        page = chunk.page_number or 0
        source_text = chunk.content

        if vault and access_context:
            regulated = await _resolve_regulated_chunk(session, chunk)
            if regulated:
                commercial_chunk, commercial_document = regulated
                commercial_chunk_ids.append(str(commercial_chunk.id))

                doc_violations = await validate_document_access(
                    session,
                    document=commercial_document,
                    policy=access_context.policy,
                )
                acl_violations = evaluate_chunk_acl(
                    commercial_chunk.acl_json,
                    request_client_id=client_id,
                    user_identity=user_identity,
                    abac_attributes=abac_attributes,
                )
                if commercial_chunk.poisoned_flag:
                    acl_violations.append("poisoned_chunk_blocked")
                if doc_violations or acl_violations:
                    audit_payload["violations"].extend(doc_violations + acl_violations)
                    if access_context.policy_mode == "enforce":
                        continue

                source_text = await _materialize_chunk_text(
                    session=session,
                    client_id=client_id,
                    fallback_text=chunk.content,
                    commercial_chunk=commercial_chunk,
                )
                poison = await analyze_and_record_poisoning(session, vault_id=vault.id, text=source_text)
                if poison.flagged:
                    audit_payload["violations"].append(poison.alert_type)
                    commercial_chunk.poisoned_flag = True
                    if access_context.policy_mode == "enforce":
                        continue
                source_text = sanitize_retrieval_text(source_text)

        sources.append(EnterpriseSource(
            document_id=chunk.document_id,
            filename=doc.original_filename if doc else "unknown",
            page=page,
            chunk_index=chunk.chunk_index,
            text=source_text,
            score=float(score),
        ))
        all_scores.append(float(score))
        if access_context and len(sources) >= access_context.max_context_chunks:
            break

    audit_payload["policy_result"] = "deny" if audit_payload["violations"] and access_context and access_context.policy_mode == "enforce" else ("report_only" if audit_payload["violations"] else "allow")
    audit_payload["retrieval_hash"] = hash_payload(
        {
            "question": question,
            "source_hashes": [hash_payload({"doc": str(src.document_id), "idx": src.chunk_index, "text": src.text}) for src in sources],
            "commercial_chunk_ids": commercial_chunk_ids,
        }
    )
    if return_audit:
        return sources, all_scores, sanitize_report_payload(audit_payload)
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


async def _resolve_regulated_chunk(
    session: AsyncSession,
    chunk: RAGDocumentChunk,
) -> tuple[CommercialRAGChunk, CommercialRAGDocument] | None:
    metadata = chunk.metadata_json or {}
    commercial_chunk_id = metadata.get("commercial_chunk_id")
    if not commercial_chunk_id:
        return None
    commercial_chunk = await session.get(CommercialRAGChunk, uuid.UUID(str(commercial_chunk_id)))
    if commercial_chunk is None:
        return None
    commercial_document = await session.get(CommercialRAGDocument, commercial_chunk.document_id)
    if commercial_document is None:
        return None
    return commercial_chunk, commercial_document


async def _materialize_chunk_text(
    session: AsyncSession,
    *,
    client_id: uuid.UUID,
    fallback_text: str,
    commercial_chunk: CommercialRAGChunk,
) -> str:
    if commercial_chunk.encrypted_payload:
        artifact_id = (commercial_chunk.acl_json or {}).get("encryption_artifact_id")
        if artifact_id:
            artifact = await session.get(CommercialEncryptedArtifact, uuid.UUID(str(artifact_id)))
            if artifact is not None:
                svc = TenantEncryptionService(settings)
                return await svc.decrypt_payload(session, artifact)
        return sanitize_chunk_preview(fallback_text)
    return fallback_text


def sanitize_retrieval_text(text: str) -> str:
    sanitized = sanitize_text(text, max_len=4000)
    sanitized = re.sub(r"(?i)ignore previous instructions", "[sanitized-instruction]", sanitized)
    sanitized = re.sub(r"(?i)system override", "[sanitized-override]", sanitized)
    sanitized = re.sub(r"(?i)(private key|secret token|root credentials)", "[sanitized-secret]", sanitized)
    return sanitized
