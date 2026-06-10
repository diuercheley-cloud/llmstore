import hashlib

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.rag import chunk_lineage, confidential_rag_vault
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
async def test_chunk_lineage(session: AsyncSession):
    vault = await confidential_rag_vault.create_vault(session, "tenant-A", "Docs")
    doc = await confidential_rag_vault.add_document_to_vault(session, vault.id, "Test Content")
    
    chunk_hash = hashlib.sha256(("Test Content_chunk0").encode()).hexdigest()
    
    lineage = await chunk_lineage.get_chunk_lineage(session, chunk_hash)
    assert lineage is not None
    assert lineage["chunk_hash"] == chunk_hash
    assert lineage["document_hash"] == doc.document_hash
    assert lineage["tenant_id"] == "tenant-A"
