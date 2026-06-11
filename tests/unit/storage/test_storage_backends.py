from __future__ import annotations

import uuid

import pytest
from app.models.core.admin_rbac import AdminAuditEvent
from app.models.core.client import Client
from app.models.rag.rag_document import RAGDocument
from app.storage import AdminAuditRecord, RAGChunkRecord, describe_storage_backend, resolve_storage_backend
from sqlalchemy import select


@pytest.mark.asyncio
async def test_resolve_storage_backend_uses_sqlite_session(session):
    backend = resolve_storage_backend(session)

    assert backend.describe().name == "sqlite"
    assert backend.describe().database_family == "sqlite"


def test_describe_storage_backend_supports_active_and_prepared_families() -> None:
    postgres = describe_storage_backend("postgresql+asyncpg://user:pass@localhost/db")
    sqlite = describe_storage_backend("sqlite+aiosqlite:////tmp/test.db")
    duckdb = describe_storage_backend("duckdb:///tmp/test.duckdb")
    clickhouse = describe_storage_backend("clickhouse://localhost:8123/default")
    opensearch = describe_storage_backend("opensearch://localhost:9200")

    assert postgres["name"] == "postgresql"
    assert sqlite["name"] == "sqlite"
    assert duckdb["name"] == "duckdb"
    assert clickhouse["readiness"] == "prepared"
    assert opensearch["readiness"] == "prepared"


@pytest.mark.asyncio
async def test_sqlite_storage_backend_document_vector_and_audit_contract(session) -> None:
    backend = resolve_storage_backend(session)

    client = Client(name="storage-test-client")
    session.add(client)
    await session.commit()
    await session.refresh(client)

    document = RAGDocument(
        id=uuid.uuid4(),
        client_id=client.id,
        filename="doc.txt",
        original_filename="doc.txt",
        content_type="text/plain",
        file_size_bytes=128,
        storage_path="/tmp/doc.txt",
        status="uploaded",
    )
    await backend.document_store.add_rag_document(document)
    await session.commit()

    listed = await backend.document_store.list_rag_documents(client.id)
    assert [item.id for item in listed] == [document.id]

    summary = await backend.document_store.summarize_rag_documents(client.id)
    assert summary["documents_count"] == 1
    assert summary["storage_bytes"] == 128

    chunk_record = RAGChunkRecord(
        id=uuid.uuid4(),
        document_id=document.id,
        client_id=client.id,
        chunk_index=0,
        page_number=1,
        content="storage backend contract",
        token_count=4,
        embedding=[0.1, 0.2, 0.3],
    )
    await backend.document_store.replace_rag_document_chunks(document.id, [chunk_record])
    await session.commit()

    chunk_ids = await backend.document_store.list_rag_chunk_ids(document.id)
    assert chunk_ids == [chunk_record.id]

    hits = await backend.vector_store.search(
        "rag_chunks",
        [0.1, 0.2, 0.3],
        limit=3,
        filters={"client_id": str(client.id), "document_id": str(document.id)},
    )
    assert hits
    assert hits[0]["id"] == str(chunk_record.id)

    await backend.document_store.add_rag_usage_event(
        client_id=client.id,
        event_type="rag_query",
        quantity=2,
    )
    await backend.document_store.add_rag_usage_event(
        client_id=client.id,
        event_type="pages_processed",
        quantity=3,
        document_id=document.id,
    )
    await session.commit()

    usage = await backend.document_store.summarize_rag_usage_events(client.id, since=document.created_at)
    assert usage["rag_query"] == 2
    assert usage["pages_processed"] == 3

    await backend.audit_store.record_admin_event(
        AdminAuditRecord(
            event_type="storage.test",
            status="ok",
            actor_identifier="pytest",
            target_type="rag_document",
            target_id=str(document.id),
        ),
        auto_commit=True,
    )
    audit_event = (await session.execute(select(AdminAuditEvent).where(AdminAuditEvent.event_type == "storage.test"))).scalar_one()
    assert audit_event.actor_identifier == "pytest"

    stored_document = await backend.document_store.get_rag_document(document.id, client_id=client.id)
    assert stored_document is not None
