import asyncio
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
async def abuse_auth_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with patch("app.db.session.SessionLocal", testing_session_local), \
         patch("app.services.backend_slot_manager.SessionLocal", testing_session_local), \
         patch("app.services.backend_slot_manager.BackendSlotManager.try_acquire", return_value=True), \
         patch("app.services.backend_slot_manager.BackendSlotManager.release", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            yield ac, testing_session_local

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def abuse_setup(abuse_auth_env):
    ac, sessionmaker = abuse_auth_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="abuse_test",
            name="Abuse Test Plan",
            rate_limit_per_minute=2,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
        )
        session.add(plan)
        await session.flush()

        active_client = Client(name="active-client", billing_plan_id=plan.id, billing_status="active")
        suspended_client = Client(name="suspended-client", billing_plan_id=plan.id, billing_status="suspended")
        blocked_client = Client(name="blocked-client", billing_plan_id=plan.id, billing_status="active", is_blocked=True)

        session.add_all([active_client, suspended_client, blocked_client])
        await session.flush()

        def make_key(client, raw):
            return ApiKey(
                client_id=client.id,
                name="test-key",
                key_prefix=short_prefix(raw),
                key_hash=hash_secret(raw),
                is_active=True,
            )

        raw_active = "sk-active-" + asyncio.get_event_loop().time().__str__()
        raw_suspended = "sk-suspended-" + asyncio.get_event_loop().time().__str__()
        raw_blocked = "sk-blocked-" + asyncio.get_event_loop().time().__str__()
        raw_revoked = "sk-revoked-" + asyncio.get_event_loop().time().__str__()

        key_active = make_key(active_client, raw_active)
        key_suspended = make_key(suspended_client, raw_suspended)
        key_blocked = make_key(blocked_client, raw_blocked)
        key_revoked = make_key(active_client, raw_revoked)
        key_revoked.is_active = False

        session.add_all([key_active, key_suspended, key_blocked, key_revoked])
        await session.commit()

        return {
            "ac": ac,
            "sessionmaker": sessionmaker,
            "active_key": raw_active,
            "suspended_key": raw_suspended,
            "blocked_key": raw_blocked,
            "revoked_key": raw_revoked,
        }


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_invalid_api_key_returns_401(mock_verify, abuse_setup):
    ac = abuse_setup["ac"]
    resp = await ac.get("/v1/models", headers={"Authorization": "Bearer invalid-test-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_revoked_api_key_returns_401(mock_verify, abuse_setup):
    ac = abuse_setup["ac"]
    resp = await ac.get("/v1/models", headers={"Authorization": f"Bearer {abuse_setup['revoked_key']}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_suspended_client_returns_402(mock_verify, abuse_setup):
    ac = abuse_setup["ac"]
    resp = await ac.get("/v1/models", headers={"Authorization": f"Bearer {abuse_setup['suspended_key']}"})
    assert resp.status_code == 402


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_blocked_client_returns_403(mock_verify, abuse_setup):
    ac = abuse_setup["ac"]
    resp = await ac.get("/v1/models", headers={"Authorization": f"Bearer {abuse_setup['blocked_key']}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_repeated_invalid_key_attempts_all_401(mock_verify, abuse_setup):
    ac = abuse_setup["ac"]
    for i in range(5):
        resp = await ac.get("/v1/models", headers={"Authorization": f"Bearer sk-invalid-{i}"})
        assert resp.status_code == 401


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_light_flood_triggers_rate_limit(mock_verify, abuse_auth_env):
    ac, sessionmaker = abuse_auth_env

    async with sessionmaker() as session:
        from app.models.core.inference_backend import InferenceBackend
        from app.models.core.model_registry import ModelRegistry

        plan = BillingPlan(
            code="flood_test",
            name="Flood Test",
            rate_limit_per_minute=2,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
        )
        session.add(plan)
        await session.flush()

        client = Client(name="flood-client", billing_plan_id=plan.id, billing_status="active")
        session.add(client)
        await session.flush()

        backend = InferenceBackend(name="flood-backend", provider="test", backend_url="http://test", is_active=True)
        session.add(backend)
        await session.flush()

        model = ModelRegistry(
            model_id="default",
            model_alias="default",
            provider="test",
            model_file="test.gguf",
            inference_backend_id=backend.id,
            is_active=True,
            is_default=True,
        )
        session.add(model)

        raw = "sk-flood-12345678"
        key = ApiKey(
            client_id=client.id,
            name="flood-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)
        await session.commit()

    statuses = []
    # Rate limit is 2 per minute. 5 requests should trigger at least one 429.
    for _ in range(5):
        resp = await ac.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw}"},
            json={"model": "default", "messages": [{"role": "user", "content": "hi"}]}
        )
        statuses.append(resp.status_code)

    # At least one request should be rate limited (429)
    assert 429 in statuses, f"Expected at least one 429 in flood test, got {statuses}"
