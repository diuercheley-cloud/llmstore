import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rag import confidential_rag_vault
from app.models.commercial_rag_vault import CommercialRAGVault

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base

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
async def test_create_vault(session: AsyncSession):
    vault = await confidential_rag_vault.create_vault(session, "tenant-123", "Finance Vault")
    assert vault.vault_name == "Finance Vault"
    assert vault.tenant_id == "tenant-123"
    assert vault.encryption_key_hash is not None

@pytest.mark.asyncio
async def test_add_document(session: AsyncSession):
    vault = await confidential_rag_vault.create_vault(session, "tenant-123", "HR Vault")
    doc = await confidential_rag_vault.add_document_to_vault(session, vault.id, "Secret salary data", "restricted")
    
    assert doc.document_hash is not None
    assert doc.classification_level == "restricted"
    assert doc.expires_at is not None
