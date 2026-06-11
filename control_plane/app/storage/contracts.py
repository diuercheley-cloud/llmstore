from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class RAGChunkRecord:
    id: UUID
    document_id: UUID
    client_id: UUID
    chunk_index: int
    page_number: int
    content: str
    token_count: int
    embedding: list[float] | None = None
    metadata_json: dict[str, Any] | None = None


@dataclass(slots=True)
class AdminAuditRecord:
    event_type: str
    status: str
    admin_user_id: UUID | None = None
    request_path: str | None = None
    request_method: str | None = None
    source_ip: str | None = None
    user_agent: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    actor_identifier: str | None = None
    metadata_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class BackendDescriptor:
    name: str
    database_family: str
    supports_transactions: bool = True
    supports_vector_indexing: bool = True
    supports_structured_audit: bool = True
    readiness: str = "active"
    notes: list[str] = field(default_factory=list)
