from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.time import utc_now
from app.models.core.admin_rbac import AdminAuditEvent
from app.models.rag.rag_document import RAGDocument
from app.models.rag.rag_document_chunk import RAGDocumentChunk
from app.models.rag.rag_usage_event import RagUsageEvent
from app.services.vectorstores.vectorstore_factory import VectorStoreFactory
from app.storage.contracts import AdminAuditRecord, RAGChunkRecord
from app.storage.interfaces import AuditStore, DocumentStore, VectorStore
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyDocumentStore(DocumentStore):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_rag_document(self, document: RAGDocument) -> RAGDocument:
        self._session.add(document)
        await self._session.flush()
        return document

    async def list_rag_documents(self, client_id: UUID) -> list[RAGDocument]:
        result = await self._session.execute(
            select(RAGDocument).where(RAGDocument.client_id == client_id).order_by(RAGDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_rag_document(self, document_id: UUID, *, client_id: UUID | None = None) -> RAGDocument | None:
        stmt = select(RAGDocument).where(RAGDocument.id == document_id)
        if client_id is not None:
            stmt = stmt.where(RAGDocument.client_id == client_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def summarize_rag_documents(self, client_id: UUID) -> dict[str, int]:
        result = await self._session.execute(
            select(
                func.count(RAGDocument.id).label("doc_count"),
                func.sum(RAGDocument.file_size_bytes).label("storage_bytes"),
            ).where(RAGDocument.client_id == client_id)
        )
        row = result.mappings().first()
        return {
            "documents_count": int((row or {}).get("doc_count") or 0),
            "storage_bytes": int((row or {}).get("storage_bytes") or 0),
        }

    async def list_rag_chunk_ids(self, document_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(RAGDocumentChunk.id).where(RAGDocumentChunk.document_id == document_id)
        )
        return list(result.scalars().all())

    async def replace_rag_document_chunks(
        self,
        document_id: UUID,
        chunk_records: Sequence[RAGChunkRecord],
    ) -> list[RAGDocumentChunk]:
        await self._session.execute(delete(RAGDocumentChunk).where(RAGDocumentChunk.document_id == document_id))
        chunks: list[RAGDocumentChunk] = []
        for record in chunk_records:
            chunk = RAGDocumentChunk(
                id=record.id,
                document_id=record.document_id,
                client_id=record.client_id,
                chunk_index=record.chunk_index,
                page_number=record.page_number,
                content=record.content,
                token_count=record.token_count,
                embedding=record.embedding,
                metadata_json=record.metadata_json,
            )
            self._session.add(chunk)
            chunks.append(chunk)
        await self._session.flush()
        return chunks

    async def get_rag_chunks(self, chunk_ids: Sequence[UUID]) -> list[RAGDocumentChunk]:
        if not chunk_ids:
            return []
        result = await self._session.execute(
            select(RAGDocumentChunk)
            .where(RAGDocumentChunk.id.in_(list(chunk_ids)))
            .order_by(RAGDocumentChunk.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_rag_documents_by_ids(self, document_ids: Sequence[UUID]) -> dict[UUID, RAGDocument]:
        if not document_ids:
            return {}
        result = await self._session.execute(select(RAGDocument).where(RAGDocument.id.in_(list(document_ids))))
        documents = result.scalars().all()
        return {document.id: document for document in documents}

    async def delete_rag_document(self, document: RAGDocument) -> None:
        await self._session.execute(delete(RAGDocumentChunk).where(RAGDocumentChunk.document_id == document.id))
        await self._session.delete(document)

    async def summarize_rag_usage_events(self, client_id: UUID, *, since) -> dict[str, int]:
        result = await self._session.execute(
            select(
                RagUsageEvent.event_type,
                func.sum(RagUsageEvent.quantity).label("total_quantity"),
            )
            .where(RagUsageEvent.client_id == client_id, RagUsageEvent.created_at >= since)
            .group_by(RagUsageEvent.event_type)
        )
        return {
            row["event_type"]: int(row["total_quantity"] or 0)
            for row in result.mappings().all()
        }

    async def add_rag_usage_event(
        self,
        *,
        client_id: UUID,
        event_type: str,
        quantity: int = 1,
        document_id: UUID | None = None,
        storage_bytes: int | None = None,
        tokens: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        event = RagUsageEvent(
            client_id=client_id,
            event_type=event_type,
            quantity=quantity,
            document_id=document_id,
            storage_bytes=storage_bytes,
            tokens=tokens,
            metadata_json=metadata_json,
        )
        self._session.add(event)
        await self._session.flush()


class VectorStoreAdapter(VectorStore):
    def __init__(self, session: AsyncSession):
        self._store = VectorStoreFactory.get_instance(session=session)

    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> None:
        await self._store.upsert(collection_name, id, vector, metadata=metadata, namespace=namespace)

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self._store.search(collection_name, vector, limit=limit, filters=filters, namespace=namespace)

    async def delete(self, collection_name: str, ids: list[str], namespace: str | None = None) -> None:
        await self._store.delete(collection_name, ids, namespace=namespace)

    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._store.collection_create(collection_name, dimension, metadata=metadata)

    async def collection_delete(self, collection_name: str) -> None:
        await self._store.collection_delete(collection_name)

    async def healthcheck(self) -> dict[str, Any]:
        return await self._store.healthcheck()


class SQLAlchemyAuditStore(AuditStore):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def record_admin_event(self, record: AdminAuditRecord, *, auto_commit: bool = True) -> None:
        event = AdminAuditEvent(
            admin_user_id=record.admin_user_id,
            event_type=record.event_type,
            status=record.status,
            request_path=record.request_path,
            request_method=record.request_method,
            source_ip=record.source_ip,
            user_agent=record.user_agent,
            target_type=record.target_type,
            target_id=record.target_id,
            actor_identifier=record.actor_identifier,
            metadata_json=record.metadata_json,
            created_at=record.created_at or utc_now(),
        )
        self._session.add(event)
        if not auto_commit:
            await self._session.flush()
            return
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
