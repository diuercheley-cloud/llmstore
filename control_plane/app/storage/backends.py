from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
from functools import cached_property
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.storage.contracts import BackendDescriptor
from app.storage.interfaces import AuditStore, DocumentStore, StorageBackend, VectorStore
from app.storage.sqlalchemy_backend import SQLAlchemyAuditStore, SQLAlchemyDocumentStore, VectorStoreAdapter
from sqlalchemy.ext.asyncio import AsyncSession


def _normalize_scheme(database_url: str) -> str:
    parsed = urlparse(database_url)
    scheme = parsed.scheme or database_url.split(":", 1)[0]
    return scheme.split("+", 1)[0].lower()


class _SQLStorageBackend(StorageBackend):
    descriptor: BackendDescriptor

    def __init__(self, session: AsyncSession):
        self._session = session

    @cached_property
    def document_store(self) -> DocumentStore:
        return SQLAlchemyDocumentStore(self._session)

    @cached_property
    def vector_store(self) -> VectorStore:
        return VectorStoreAdapter(self._session)

    @cached_property
    def audit_store(self) -> AuditStore:
        return SQLAlchemyAuditStore(self._session)


class PostgreSQLStorageBackend(_SQLStorageBackend):
    descriptor = BackendDescriptor(
        name="postgresql",
        database_family="postgresql",
        supports_transactions=True,
        supports_vector_indexing=True,
        supports_structured_audit=True,
        readiness="active",
    )


class SQLiteStorageBackend(_SQLStorageBackend):
    descriptor = BackendDescriptor(
        name="sqlite",
        database_family="sqlite",
        supports_transactions=True,
        supports_vector_indexing=True,
        supports_structured_audit=True,
        readiness="active",
        notes=["Vector similarity falls back to persisted embeddings when pgvector is unavailable."],
    )


class DuckDBStorageBackend(_SQLStorageBackend):
    descriptor = BackendDescriptor(
        name="duckdb",
        database_family="duckdb",
        supports_transactions=True,
        supports_vector_indexing=True,
        supports_structured_audit=True,
        readiness="active",
        notes=["Requires a DuckDB-compatible SQLAlchemy session or adapter at runtime."],
    )


class PreparedStorageBackend(StorageBackend):
    descriptor: BackendDescriptor

    def __init__(self, details: str | None = None):
        if details:
            self.descriptor = replace(self.descriptor, notes=[*self.descriptor.notes, details])

    @property
    def document_store(self) -> DocumentStore:
        raise NotImplementedError(f"{self.descriptor.name} backend is prepared but not active")

    @property
    def vector_store(self) -> VectorStore:
        raise NotImplementedError(f"{self.descriptor.name} backend is prepared but not active")

    @property
    def audit_store(self) -> AuditStore:
        raise NotImplementedError(f"{self.descriptor.name} backend is prepared but not active")


class ClickHouseStorageBackend(PreparedStorageBackend):
    descriptor = BackendDescriptor(
        name="clickhouse",
        database_family="clickhouse",
        supports_transactions=False,
        supports_vector_indexing=False,
        supports_structured_audit=True,
        readiness="prepared",
        notes=["Reserved for high-volume analytics and audit sinks."],
    )


class OpenSearchStorageBackend(PreparedStorageBackend):
    descriptor = BackendDescriptor(
        name="opensearch",
        database_family="opensearch",
        supports_transactions=False,
        supports_vector_indexing=True,
        supports_structured_audit=False,
        readiness="prepared",
        notes=["Reserved for search-native document and vector workloads."],
    )


def resolve_storage_backend(
    session: AsyncSession | None = None,
    *,
    database_url: str | None = None,
) -> StorageBackend:
    if session is None and database_url is None:
        database_url = get_settings().database_url

    if session is not None:
        bind = session.bind
        if bind is not None:
            dialect = bind.dialect.name.lower()
            if dialect == "postgresql":
                return PostgreSQLStorageBackend(session)
            if dialect == "sqlite":
                return SQLiteStorageBackend(session)
            if dialect == "duckdb":
                return DuckDBStorageBackend(session)

    if database_url is None:
        raise ValueError("database_url or session is required to resolve the storage backend")

    scheme = _normalize_scheme(database_url)
    if scheme in {"postgres", "postgresql"}:
        if session is None:
            raise ValueError("PostgreSQL storage backend requires an active session")
        return PostgreSQLStorageBackend(session)
    if scheme == "sqlite":
        if session is None:
            raise ValueError("SQLite storage backend requires an active session")
        return SQLiteStorageBackend(session)
    if scheme == "duckdb":
        if session is None:
            raise ValueError("DuckDB storage backend requires an active session")
        return DuckDBStorageBackend(session)
    if scheme == "clickhouse":
        return ClickHouseStorageBackend()
    if scheme == "opensearch":
        return OpenSearchStorageBackend()
    raise ValueError(f"Unsupported storage backend scheme: {scheme}")


def describe_storage_backend(database_url: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    scheme = _normalize_scheme(database_url or settings.database_url)
    if scheme in {"postgres", "postgresql"}:
        return asdict(PostgreSQLStorageBackend.descriptor)
    if scheme == "sqlite":
        return asdict(SQLiteStorageBackend.descriptor)
    if scheme == "duckdb":
        return asdict(DuckDBStorageBackend.descriptor)
    if scheme == "clickhouse":
        return asdict(ClickHouseStorageBackend.descriptor)
    if scheme == "opensearch":
        return asdict(OpenSearchStorageBackend.descriptor)
    raise ValueError(f"Unsupported storage backend scheme: {scheme}")
