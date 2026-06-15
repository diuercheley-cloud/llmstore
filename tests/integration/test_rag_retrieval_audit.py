import httpx
import pytest
import pytest_asyncio
from app.api.rag_enterprise import admin_router
from app.db.base import Base
from app.db.session import get_db_session
from app.models.commercial.commercial_rag_vault_vault import (
    CommercialRAGRetrievalAudit,
    CommercialRAGVault,
)
from app.models.core.client import Client
from app.services.rag.rag_audit import record_retrieval_audit
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_immutable_retrieval_audit_created(session: AsyncSession):
    client = Client(name="tenant")
    session.add(client)
    await session.flush()
    vault = CommercialRAGVault(
        client_id=client.id,
        vault_name="regulated",
        vault_mode="confidential",
        encryption_required=True,
        retrieval_mode="hybrid",
        immutable_audit_enabled=True,
    )
    session.add(vault)
    await session.flush()

    audit = await record_retrieval_audit(
        session,
        vault=vault,
        client_id=client.id,
        request_payload={"question": "where is invoice 123"},
        retrieval_payload={"source_ids": ["a", "b"]},
        user_identity="alice@example.com",
        retrieved_chunk_count=2,
        policy_result="allow",
        model_id="local-model",
    )
    await session.commit()

    assert audit.request_hash
    assert audit.retrieval_hash
    assert audit.immutable_hash
    rows = (await session.execute(select(CommercialRAGRetrievalAudit))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_admin_retrieval_audit_auth(session: AsyncSession):
    app = FastAPI()
    app.include_router(admin_router)

    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        unauthorized = await client.get("/admin/rag/retrieval-audit")
        assert unauthorized.status_code == 401

        authorized = await client.get(
            "/admin/rag/retrieval-audit", headers={"X-Admin-Token": "test-admin-token"}
        )
        assert authorized.status_code == 200

    app.dependency_overrides.clear()
