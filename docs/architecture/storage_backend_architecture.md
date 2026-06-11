# StorageBackend Architecture

## Objective

`StorageBackend` isolates business services from database-specific persistence details. Services consume stable interfaces while backend selection is resolved from the active session or database URL.

## Interfaces

The storage layer lives in `control_plane/app/storage/` and exposes four contracts:

- `StorageBackend`: aggregate root for a concrete persistence family.
- `DocumentStore`: document and usage persistence used by RAG flows.
- `VectorStore`: vector indexing and similarity search abstraction.
- `AuditStore`: structured audit event sink.

## Active backends

### PostgreSQL

- Transactional SQL persistence through SQLAlchemy.
- Vector path delegated to the existing vector provider stack, with `pgvector` as the natural in-database option.
- Structured audit events persisted in relational tables.

### SQLite

- Transactional SQL persistence through SQLAlchemy.
- Vector operations reuse the same provider contract; when `pgvector` is unavailable the system falls back to persisted embeddings and in-process cosine search.
- Useful for `lite`, tests, and single-node deployments.

### DuckDB

- Same service contract as the SQLAlchemy-backed stores.
- Intended for local analytical or embedded deployments once a DuckDB-compatible engine/session is wired in.
- Current layer is implementation-ready at the contract level and only depends on runtime session provisioning.

## Prepared backends

### ClickHouse

- Reserved for high-volume analytical and audit-heavy workloads.
- Marked as `prepared`; no runtime store is activated yet.

### OpenSearch

- Reserved for search-native document and vector workloads.
- Marked as `prepared`; no runtime store is activated yet.

## Current service migration

The first migration slice routes these business services through the new interfaces:

- `app.services.rag_usage`
- `app.services.rag_processor`
- `app.api.rag`
- `app.services.admin_rbac.record_admin_audit_event`

This keeps the public API unchanged while moving persistence decisions behind `StorageBackend`.

## Resolution model

`resolve_storage_backend(...)` chooses a backend from:

1. the active SQLAlchemy session dialect, when available;
2. the configured `DATABASE_URL` scheme otherwise.

This means business logic no longer branches on `sqlite`, `postgresql`, or future engines directly.

## Extension path

To migrate more domains, services should depend on `DocumentStore`, `VectorStore`, or `AuditStore` instead of importing ORM tables or provider factories directly. New persistence families only need a `StorageBackend` implementation plus contract tests.
