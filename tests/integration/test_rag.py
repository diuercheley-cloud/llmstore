import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.api.rag import router as rag_router
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.models.rag.rag_document import RAGDocument
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def client_and_session(isolated_db_url, fake_redis):
    test_app = FastAPI()
    test_app.include_router(rag_router)
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = override_get_db_session
    test_app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as ac:
        yield ac, testing_session_local

    test_app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_rag_upload_unauthorized(client_and_session):
    async_client, _ = client_and_session
    response = await async_client.post("/v1/rag/files", files={"file": ("test.pdf", b"pdf content")})
    assert response.status_code == 401

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_rag_upload_success(mock_verify, client_and_session):
    async_client, sessionmaker = client_and_session
    
    async with sessionmaker() as session:
        client = Client(name="test-client", billing_status="active")
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        # Prefix MUST be exactly 12 chars if the auth service expects that
        prefix = "sk-test-1234"
        api_key = ApiKey(client_id=client.id, name="test", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        with patch("app.api.rag.redis_client") as mock_redis:
            mock_redis.rpush = AsyncMock()
            
            response = await async_client.post(
                "/v1/rag/files",
                headers=headers,
                files={"file": ("test.pdf", b"%PDF-1.4 content")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["original_filename"] == "test.pdf"
            
            # Verify DB
            doc_id = uuid.UUID(data["id"])
            doc = (await session.execute(select(RAGDocument).where(RAGDocument.id == doc_id))).scalar_one()
            assert doc.client_id == client.id
