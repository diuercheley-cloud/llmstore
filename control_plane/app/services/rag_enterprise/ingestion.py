import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.client import Client
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.services.rag_enterprise.parsers import parse_file, get_parser_status
from app.services.rag_enterprise.chunking import chunk_text
from app.services.rag_enterprise.schemas import ChunkingConfig, ChunkStrategy, SUPPORTED_EXTENSIONS
from app.services.rag_enterprise.embeddings import get_enterprise_embedding_service
from app.services.rag_enterprise.policies import (
    EnterpriseRagPolicy,
    check_quota_documents,
    check_quota_storage,
    check_quota_pages,
    check_file_type_allowed,
    resolve_enterprise_rag_policy,
    is_cloud_embedding_allowed,
)
from app.services.rag_usage import record_rag_event
from app.utils.token_estimator import estimate_tokens_from_text

logger = logging.getLogger(__name__)
settings = get_settings()


async def ingest_document(
    session: AsyncSession,
    client_id: uuid.UUID,
    file_path: str,
    original_filename: str,
    content_type: str,
    file_size_bytes: int,
    collection_id: Optional[uuid.UUID] = None,
    tags: Optional[List[str]] = None,
    retention_days: Optional[int] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    strategy: str = "fixed",
) -> RAGDocument:
    client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
    if not client:
        raise ValueError(f"Client {client_id} not found")

    policy = await resolve_enterprise_rag_policy(session, client)
    if not policy.rag_enabled:
        raise PermissionError("RAG is not enabled for this client")

    ext = os.path.splitext(original_filename)[1].lower()
    allowed, msg = await check_file_type_allowed(original_filename, policy)
    if not allowed:
        raise ValueError(msg)

    doc_ok, doc_msg = await check_quota_documents(session, client_id, policy)
    if not doc_ok:
        raise ValueError(doc_msg)

    storage_ok, storage_msg = await check_quota_storage(session, client_id, policy, file_size_bytes)
    if not storage_ok:
        raise ValueError(storage_msg)

    parser_status = get_parser_status(ext)
    if not parser_status.available:
        raise ImportError(
            f"Parser for {ext} is not available. "
            f"Dependency: {parser_status.dependency}. "
            f"Remediation: {parser_status.remediation}"
        )

    parse_result = await parse_file(file_path, ext)

    pages_ok, pages_msg = await check_quota_pages(session, client_id, policy, len(parse_result.pages))
    if not pages_ok:
        raise ValueError(pages_msg)

    chunk_config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=ChunkStrategy(strategy),
    )

    raw_chunks = chunk_text(parse_result.text, chunk_config)

    embedding_service = get_enterprise_embedding_service()
    cloud_allowed = await is_cloud_embedding_allowed(client, policy)
    texts = [c.content for c in raw_chunks]
    embeddings = await embedding_service.embed_batch(texts, cloud_allowed=cloud_allowed)

    doc_id = uuid.uuid4()
    retention_until = None
    if retention_days:
        retention_until = utc_now() + timedelta(days=retention_days)

    doc = RAGDocument(
        id=doc_id,
        client_id=client_id,
        filename=os.path.basename(file_path),
        original_filename=original_filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        storage_path=file_path,
        status="indexed",
        page_count=len(parse_result.pages),
        chunk_count=len(raw_chunks),
    )
    session.add(doc)
    await session.flush()

    for i, (chunk_data, embedding) in enumerate(zip(raw_chunks, embeddings)):
        metadata = dict(chunk_data.metadata)
        if tags:
            metadata["tags"] = tags
        if collection_id:
            metadata["collection_id"] = str(collection_id)
        metadata["tenant_id"] = str(client_id)
        metadata["document_id"] = str(doc_id)
        metadata["source_file"] = original_filename

        chunk = RAGDocumentChunk(
            document_id=doc_id,
            client_id=client_id,
            chunk_index=i,
            page_number=chunk_data.page_number or 1,
            content=chunk_data.content,
            token_count=estimate_tokens_from_text(chunk_data.content),
            embedding=embedding,
            metadata_json=metadata,
        )
        session.add(chunk)

    doc.status = "indexed"
    doc.processed_at = utc_now()

    await record_rag_event(session, client_id, "document_uploaded", document_id=doc_id, storage_bytes=file_size_bytes)
    await record_rag_event(session, client_id, "pages_processed", quantity=len(parse_result.pages), document_id=doc_id)

    await session.commit()
    await session.refresh(doc)

    logger.info(
        f"Ingested document {doc_id} ({original_filename}) for client {client_id}: "
        f"{doc.chunk_count} chunks, {doc.page_count} pages"
    )

    return doc


async def delete_enterprise_document(
    session: AsyncSession,
    document: RAGDocument,
):
    await session.execute(sa_delete(RAGDocumentChunk).where(RAGDocumentChunk.document_id == document.id))
    if document.storage_path and os.path.exists(document.storage_path):
        try:
            os.remove(document.storage_path)
        except Exception as e:
            logger.error(f"Failed to delete file {document.storage_path}: {e}")
    await session.delete(document)
