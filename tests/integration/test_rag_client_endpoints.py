import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.models.rag.rag_document import RAGDocument
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def client_and_session(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, testing_session_local

    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_client_rag_endpoints_unauthorized(client_and_session):
    async_client, _ = client_and_session
    response = await async_client.get("/client/rag/documents")
    assert response.status_code == 401

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_client_rag_upload_and_list(mock_verify, client_and_session):
    async_client, sessionmaker = client_and_session
    
    async with sessionmaker() as session:
        client = Client(name="test-client", billing_status="active")
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        prefix = "sk-test-1234"
        api_key = ApiKey(client_id=client.id, name="test", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        with patch("app.api.rag.redis_client") as mock_redis:
            mock_redis.rpush = AsyncMock()
            
            # 1. Upload
            response = await async_client.post(
                "/client/rag/documents",
                headers=headers,
                files={"file": ("test.txt", b"plain text content")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["original_filename"] == "test.txt"
            doc_id = data["id"]
            
            # 2. List
            response = await async_client.get("/client/rag/documents", headers=headers)
            assert response.status_code == 200
            list_data = response.json()["data"]
            assert len(list_data) == 1
            assert list_data[0]["id"] == doc_id
            
            # 3. Get Details
            response = await async_client.get(f"/client/rag/documents/{doc_id}", headers=headers)
            assert response.status_code == 200
            assert response.json()["original_filename"] == "test.txt"
            
            # 4. Delete
            response = await async_client.delete(f"/client/rag/documents/{doc_id}", headers=headers)
            assert response.status_code == 200
            
            # Verify deleted from DB
            doc = (await session.execute(select(RAGDocument).where(RAGDocument.id == uuid.UUID(doc_id)))).scalar_one_or_none()
            assert doc is None
