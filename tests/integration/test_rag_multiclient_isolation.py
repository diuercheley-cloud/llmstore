from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def clients_and_session(isolated_db_url, fake_redis):
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
@patch("app.services.auth.verify_secret", return_value=True)
async def test_rag_multiclient_isolation(mock_verify, clients_and_session):
    async_client, sessionmaker = clients_and_session
    
    async with sessionmaker() as session:
        # Client A
        client_a = Client(name="client-a", billing_status="active")
        session.add(client_a)
        # Client B
        client_b = Client(name="client-b", billing_status="active")
        session.add(client_b)
        await session.commit()
        await session.refresh(client_a)
        await session.refresh(client_b)
        
        # API Keys
        prefix_a = "sk-cl-a-1234" # 12 chars
        api_key_a = ApiKey(client_id=client_a.id, name="a", key_prefix=prefix_a, key_hash="ha")
        session.add(api_key_a)
        
        prefix_b = "sk-cl-b-1234" # 12 chars
        api_key_b = ApiKey(client_id=client_b.id, name="b", key_prefix=prefix_b, key_hash="hb")
        session.add(api_key_b)
        await session.commit()
        
        headers_a = {"Authorization": f"Bearer {prefix_a}.val"}
        headers_b = {"Authorization": f"Bearer {prefix_b}.val"}
        
        with patch("app.api.rag.redis_client") as mock_redis:
            mock_redis.rpush = AsyncMock()
            
            # 1. Client A uploads a file
            response = await async_client.post(
                "/client/rag/documents",
                headers=headers_a,
                files={"file": ("doc_a.txt", b"secret a content")}
            )
            assert response.status_code == 200
            doc_a_id = response.json()["id"]
            
            # 2. Client B lists files - should be empty
            response = await async_client.get("/client/rag/documents", headers=headers_b)
            assert response.status_code == 200
            assert len(response.json()["data"]) == 0
            
            # 3. Client B tries to GET doc_a_id - should be 404
            response = await async_client.get(f"/client/rag/documents/{doc_a_id}", headers=headers_b)
            assert response.status_code == 404
            
            # 4. Client B tries to DELETE doc_a_id - should be 404
            response = await async_client.delete(f"/client/rag/documents/{doc_a_id}", headers=headers_b)
            assert response.status_code == 404
            
            # 5. Verify Client A still has the file
            response = await async_client.get("/client/rag/documents", headers=headers_a)
            assert len(response.json()["data"]) == 1
