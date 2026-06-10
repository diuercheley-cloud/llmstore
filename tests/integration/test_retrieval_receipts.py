import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.rag import confidential_rag_vault, retrieval_receipts
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
async def test_generate_retrieval_receipt(session: AsyncSession):
    vault = await confidential_rag_vault.create_vault(session, "tenant-1", "V1")
    
    receipt = await retrieval_receipts.generate_retrieval_receipt(
        session, vault.id, "sess-01", "What is the capital of France?", ["hash1", "hash2"]
    )
    
    assert receipt.session_id == "sess-01"
    assert len(receipt.retrieved_chunk_hashes) == 2
    assert receipt.receipt_hash is not None
