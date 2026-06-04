import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def tts_test_env(isolated_db_url, fake_redis):
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

@pytest.fixture
async def tts_setup(tts_test_env):
    ac, sessionmaker = tts_test_env
    
    async with sessionmaker() as session:
        # Create a plan with TTS enabled
        plan = BillingPlan(
            code="tts_plan",
            name="TTS Plan",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=5000,
            monthly_token_quota=10000,
            max_output_tokens=100,
            tts_enabled=True,
            tts_chars_per_request=100,
            tts_chars_per_day=500,
            tts_chars_per_month=2000
        )
        session.add(plan)
        
        # Create a plan with TTS disabled
        free_plan = BillingPlan(
            code="no_tts_plan",
            name="No TTS Plan",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=5000,
            monthly_token_quota=10000,
            max_output_tokens=100,
            tts_enabled=False
        )
        session.add(free_plan)
        await session.flush()
        
        # Create a client
        client = Client(name="TTS Test Client", billing_plan_id=plan.id)
        session.add(client)
        
        free_client_obj = Client(name="Free Test Client", billing_plan_id=free_plan.id)
        session.add(free_client_obj)
        await session.flush()
        
        # Create API Keys
        raw_key = "sk-tts-" + uuid.uuid4().hex
        api_key = ApiKey(
            client_id=client.id,
            name="TTS Key",
            key_prefix=short_prefix(raw_key),
            key_hash=hash_secret(raw_key),
            is_active=True
        )
        session.add(api_key)
        
        free_raw_key = "sk-free-" + uuid.uuid4().hex
        free_api_key = ApiKey(
            client_id=free_client_obj.id,
            name="Free Key",
            key_prefix=short_prefix(free_raw_key),
            key_hash=hash_secret(free_raw_key),
            is_active=True
        )
        session.add(free_api_key)
        await session.commit()
        
        return {
            "ac": ac,
            "sessionmaker": sessionmaker,
            "tts_client": client,
            "tts_key": raw_key,
            "free_client": free_client_obj,
            "free_key": free_raw_key
        }

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_blocked_for_free_client(mock_verify, tts_setup):
    data = tts_setup
    ac = data["ac"]
    api_key = data["free_key"]
    
    response = await ac.post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {api_key}"},
        data={"text": "Hello world"}
    )
    assert response.status_code == 403
    assert "TTS feature is not enabled for your plan" in response.json()["detail"]

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_quota_request_limit(mock_verify, tts_setup):
    data = tts_setup
    ac = data["ac"]
    api_key = data["tts_key"]
    
    # Request with more than 100 chars
    large_text = "a" * 101
    response = await ac.post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {api_key}"},
        data={"text": large_text}
    )
    assert response.status_code == 413
    assert "exceeds maximum characters per request" in response.json()["detail"]

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_quota_daily_limit(mock_verify, tts_setup):
    data = tts_setup
    ac = data["ac"]
    sessionmaker = data["sessionmaker"]
    client = data["tts_client"]
    api_key = data["tts_key"]
    
    from app.services.tts_usage import record_tts_event
    
    async with sessionmaker() as session:
        # Consume almost all daily quota
        await record_tts_event(session, client.id, 450)
        await session.commit()
    
    # Request 60 chars (total 510 > 500)
    response = await ac.post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {api_key}"},
        data={"text": "a" * 60}
    )
    assert response.status_code == 429
    assert "Daily TTS character quota exceeded" in response.json()["detail"]
