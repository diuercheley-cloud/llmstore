import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.rag import confidential_rag_vault, context_sanitizer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_blocked(session: AsyncSession):
    vault_a = await confidential_rag_vault.create_vault(session, "tenant-A", "Vault A")
    doc_a = await confidential_rag_vault.add_document_to_vault(
        session, vault_a.id, "A Content", "internal"
    )

    # Try retrieving with tenant-B
    safe_docs, blocks = await context_sanitizer.sanitize_retrieval(
        session, vault_a.id, "sess-1", "queryhash", [doc_a], "tenant-B"
    )

    assert len(safe_docs) == 0
    assert "cross_tenant_blocked" in blocks


@pytest.mark.asyncio
async def test_classification_mismatch_blocked(session: AsyncSession):
    vault_a = await confidential_rag_vault.create_vault(session, "tenant-A", "Vault A")
    doc_a = await confidential_rag_vault.add_document_to_vault(
        session, vault_a.id, "Restricted Content", "restricted"
    )

    safe_docs, blocks = await context_sanitizer.sanitize_retrieval(
        session, vault_a.id, "sess-2", "queryhash", [doc_a], "tenant-A"
    )

    assert len(safe_docs) == 0
    assert any("blocked_restricted_doc" in b for b in blocks)
