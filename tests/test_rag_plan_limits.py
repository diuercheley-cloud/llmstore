from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def client_with_limits(isolated_db_url, fake_redis):
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
async def test_rag_max_documents_limit(mock_verify, client_with_limits):
    async_client, sessionmaker = client_with_limits
    
    async with sessionmaker() as session:
        # Create plan with 1 document limit
        plan = BillingPlan(
            code="rag_limited",
            name="RAG Limited",
            rag_enabled=True,
            rag_max_documents=1,
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            monthly_token_quota=10000,
            max_output_tokens=512
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        
        client = Client(name="limited-client", billing_status="active", billing_plan_id=plan.id)
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        prefix = "sk-limited-1"
        api_key = ApiKey(client_id=client.id, name="k", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        with patch("app.api.rag.redis_client") as mock_redis:
            mock_redis.rpush = AsyncMock()
            
            # 1. First upload - should succeed
            response = await async_client.post(
                "/client/rag/documents",
                headers=headers,
                files={"file": ("doc1.txt", b"content 1")}
            )
            assert response.status_code == 200
            
            # 2. Second upload - should fail (429 rag_limit_exceeded)
            response = await async_client.post(
                "/client/rag/documents",
                headers=headers,
                files={"file": ("doc2.txt", b"content 2")}
            )
            assert response.status_code == 429
            assert response.json()["error"] == "rag_limit_exceeded"
            assert response.json()["limit"] == "rag_max_documents"
