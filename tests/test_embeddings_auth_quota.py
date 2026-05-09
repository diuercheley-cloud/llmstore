import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

from app.main import app
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan

@pytest_asyncio.fixture
async def client_with_embeddings_plan(isolated_db_url, fake_redis):
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
async def test_embeddings_plan_disabled(mock_verify, client_with_embeddings_plan):
    async_client, sessionmaker = client_with_embeddings_plan
    
    async with sessionmaker() as session:
        # Create plan with embeddings disabled
        plan = BillingPlan(
            code="no_embeddings",
            name="No Embeddings",
            embeddings_enabled=False,
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
        
        # Prefix MUST be 12 chars for require_client
        prefix = "sk-no-emb-12"
        api_key = ApiKey(client_id=client.id, name="k", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        response = await async_client.post(
            "/v1/embeddings",
            headers=headers,
            json={"model": "t", "input": "test"}
        )
        assert response.status_code == 403
        assert "not enabled for your plan" in response.text

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_embeddings_input_limit(mock_verify, client_with_embeddings_plan):
    async_client, sessionmaker = client_with_embeddings_plan
    
    async with sessionmaker() as session:
        plan = BillingPlan(
            code="emb_limited",
            name="Emb Limited",
            embeddings_enabled=True,
            embeddings_max_inputs_per_request=2,
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            monthly_token_quota=10000,
            max_output_tokens=512
        )
        session.add(plan)
        await session.commit()
        
        client = Client(name="client", billing_status="active", billing_plan_id=plan.id)
        session.add(client)
        await session.commit()
        
        prefix = "sk-emb-lim-1"
        api_key = ApiKey(client_id=client.id, name="k", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        # Should fail with 3 inputs
        response = await async_client.post(
            "/v1/embeddings",
            headers=headers,
            json={"model": "t", "input": ["a", "b", "c"]}
        )
        assert response.status_code == 400
        assert "too many inputs" in response.text
