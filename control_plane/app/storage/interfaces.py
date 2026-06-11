from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.rag.rag_document import RAGDocument
from app.models.rag.rag_document_chunk import RAGDocumentChunk
from app.storage.contracts import AdminAuditRecord, BackendDescriptor, RAGChunkRecord


class DocumentStore(ABC):
    @abstractmethod
    async def add_rag_document(self, document: RAGDocument) -> RAGDocument:
        raise NotImplementedError

    @abstractmethod
    async def list_rag_documents(self, client_id: UUID) -> list[RAGDocument]:
        raise NotImplementedError

    @abstractmethod
    async def get_rag_document(self, document_id: UUID, *, client_id: UUID | None = None) -> RAGDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def summarize_rag_documents(self, client_id: UUID) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def list_rag_chunk_ids(self, document_id: UUID) -> list[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def replace_rag_document_chunks(
        self,
        document_id: UUID,
        chunk_records: Sequence[RAGChunkRecord],
    ) -> list[RAGDocumentChunk]:
        raise NotImplementedError

    @abstractmethod
    async def get_rag_chunks(self, chunk_ids: Sequence[UUID]) -> list[RAGDocumentChunk]:
        raise NotImplementedError

    @abstractmethod
    async def get_rag_documents_by_ids(self, document_ids: Sequence[UUID]) -> dict[UUID, RAGDocument]:
        raise NotImplementedError

    @abstractmethod
    async def delete_rag_document(self, document: RAGDocument) -> None:
        raise NotImplementedError

    @abstractmethod
    async def summarize_rag_usage_events(self, client_id: UUID, *, since: datetime) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, collection_name: str, ids: list[str], namespace: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def collection_delete(self, collection_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> dict[str, Any]:
        raise NotImplementedError


class AuditStore(ABC):
    @abstractmethod
    async def record_admin_event(self, record: AdminAuditRecord, *, auto_commit: bool = True) -> None:
        raise NotImplementedError


class StorageBackend(ABC):
    descriptor: BackendDescriptor

    @property
    @abstractmethod
    def document_store(self) -> DocumentStore:
        raise NotImplementedError

    @property
    @abstractmethod
    def vector_store(self) -> VectorStore:
        raise NotImplementedError

    @property
    @abstractmethod
    def audit_store(self) -> AuditStore:
        raise NotImplementedError

    def describe(self) -> BackendDescriptor:
        return self.descriptor
