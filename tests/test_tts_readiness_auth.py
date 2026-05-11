import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client


@pytest_asyncio.fixture
async def tts_auth_env(isolated_db_url, fake_redis):
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
async def tts_auth_setup(tts_auth_env):
    ac, sessionmaker = tts_auth_env

    async with sessionmaker() as session:
        enabled_plan = BillingPlan(
            code="tts_auth_enabled",
            name="TTS Auth Enabled",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=5000,
            monthly_token_quota=10000,
            max_output_tokens=100,
            tts_enabled=True,
            tts_chars_per_request=100,
            tts_chars_per_day=500,
            tts_chars_per_month=2000,
        )
        disabled_plan = BillingPlan(
            code="tts_auth_disabled",
            name="TTS Auth Disabled",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=5000,
            monthly_token_quota=10000,
            max_output_tokens=100,
            tts_enabled=False,
        )
        session.add_all([enabled_plan, disabled_plan])
        await session.flush()

        allowed_client = Client(name="TTS Allowed Client", billing_plan_id=enabled_plan.id)
        denied_client = Client(name="TTS Denied Client", billing_plan_id=disabled_plan.id)
        suspended_client = Client(name="TTS Suspended Client", billing_plan_id=enabled_plan.id, billing_status="suspended")
        session.add_all([allowed_client, denied_client, suspended_client])
        await session.flush()

        allowed_key = "sk-tts-allowed-" + uuid.uuid4().hex
        denied_key = "sk-tts-denied-" + uuid.uuid4().hex
        suspended_key = "sk-tts-suspended-" + uuid.uuid4().hex
        session.add_all(
            [
                ApiKey(client_id=allowed_client.id, name="Allowed", key_prefix=short_prefix(allowed_key), key_hash=hash_secret(allowed_key), is_active=True),
                ApiKey(client_id=denied_client.id, name="Denied", key_prefix=short_prefix(denied_key), key_hash=hash_secret(denied_key), is_active=True),
                ApiKey(client_id=suspended_client.id, name="Suspended", key_prefix=short_prefix(suspended_key), key_hash=hash_secret(suspended_key), is_active=True),
            ]
        )
        await session.commit()

    return {
        "ac": ac,
        "allowed_key": allowed_key,
        "denied_key": denied_key,
        "suspended_key": suspended_key,
    }


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_readiness_rejects_client_without_tts_permission(mock_verify, tts_auth_setup):
    response = await tts_auth_setup["ac"].post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {tts_auth_setup['denied_key']}"},
        data={"text": "blocked"},
    )

    assert response.status_code == 403
    assert "not enabled for your plan" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_readiness_keeps_suspended_client_blocked(mock_verify, tts_auth_setup):
    response = await tts_auth_setup["ac"].post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {tts_auth_setup['suspended_key']}"},
        data={"text": "blocked"},
    )

    assert response.status_code == 402
    assert response.json()["detail"]["error"] == "billing_suspended"


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_readiness_invalid_bearer_returns_specific_401(mock_verify, tts_auth_setup):
    response = await tts_auth_setup["ac"].post(
        "/pocket-tts/tts",
        headers={"Authorization": "Bearer sk-missing-abcdef123456"},  # FAKE TEST KEY - DO NOT USE
        data={"text": "blocked"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid api key"
