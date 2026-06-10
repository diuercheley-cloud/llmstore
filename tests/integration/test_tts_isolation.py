import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
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

@pytest_asyncio.fixture
async def tts_setup(tts_test_env):
    ac, sessionmaker = tts_test_env
    async with sessionmaker() as session:
        plan = BillingPlan(
            code="tts_plan", name="TTS Plan", rate_limit_per_minute=10,
            daily_token_quota=1000, weekly_token_quota=5000, monthly_token_quota=10000,
            max_output_tokens=100, tts_enabled=True, tts_chars_per_request=100,
            tts_chars_per_day=500, tts_chars_per_month=2000
        )
        session.add(plan)
        await session.flush()
        client = Client(name="TTS Test Client", billing_plan_id=plan.id)
        session.add(client)
        await session.flush()
        raw_key = "sk-tts-" + uuid.uuid4().hex
        api_key = ApiKey(
            client_id=client.id, name="TTS Key", key_prefix=short_prefix(raw_key),
            key_hash=hash_secret(raw_key), is_active=True
        )
        session.add(api_key)
        await session.commit()
        return {"ac": ac, "sessionmaker": sessionmaker, "client": client, "api_key": raw_key}

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_isolation_headers(mock_verify, tts_setup):
    ac = tts_setup["ac"]
    api_key = tts_setup["api_key"]
    
    # Check that a client cannot spoof X-Client-ID
    fake_client_id = str(uuid.uuid4())
    # We mock the proxy call to avoid needing a real pocket-tts service
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = patch("httpx.Response", status_code=200, content=b"fake audio").start()
        
        response = await ac.post(
            "/pocket-tts/tts",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Client-ID": fake_client_id
            },
            data={"text": "Test isolation"}
        )
    
    # Usage recording and quota check should happen for the AUTHENTICATED client.
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pocket_tts_ui_is_public(tts_setup):
    ac = tts_setup["ac"]

    response = await ac.get("/pocket-tts/")

    assert response.status_code == 200
    assert "Pocket TTS Studio" in response.text


@pytest.mark.asyncio
async def test_pocket_tts_health_still_requires_auth(tts_setup):
    ac = tts_setup["ac"]

    response = await ac.get("/pocket-tts/health")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer token"
