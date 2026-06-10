import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.core.quota_counter import QuotaCounter
from app.models.core.tts_usage_event import TtsUsageEvent
from app.services.tts_readiness import get_or_create_tts_readiness_client
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def tts_probe_env(isolated_db_url, fake_redis):
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
async def tts_probe_setup(tts_probe_env):
    ac, sessionmaker = tts_probe_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="tts_probe_plan",
            name="TTS Probe Plan",
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
        session.add(plan)
        await session.flush()

        client = Client(name="TTS Probe Client", billing_plan_id=plan.id)
        session.add(client)
        await session.flush()

        raw_key = "sk-tts-probe-" + uuid.uuid4().hex
        api_key = ApiKey(
            client_id=client.id,
            name="TTS Probe Key",
            key_prefix=short_prefix(raw_key),
            key_hash=hash_secret(raw_key),
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

        return {
            "ac": ac,
            "sessionmaker": sessionmaker,
            "client": client,
            "api_key": raw_key,
        }


def test_get_or_create_tts_readiness_client_avoids_suspended_client():
    calls: list[tuple[str, str]] = []

    def fake_http_request(path, *, method="GET", headers=None, body=None, timeout=15):
        calls.append((method, path))
        if path == "/admin/billing/plans":
            return 200, '[{"id":"plan-disabled","code":"free","tts_enabled":false,"is_active":true},{"id":"plan-tts","code":"basic","tts_enabled":true,"is_active":true}]', {}, None
        if path == "/admin/clients":
            if method == "GET":
                return 200, '[{"id":"old-client","name":"tts-readiness-probe-client","billing_status":"suspended","is_blocked":false,"billing_plan_id":"plan-disabled"}]', {}, None
            return 201, '{"id":"new-client","name":"tts-readiness-probe-client-2","billing_status":"active","is_blocked":false,"billing_plan_id":"plan-tts"}', {}, None
        if path == "/admin/api-keys":
            return 201, '{"id":"key-1","key_prefix":"sk-test-pref","api_key":"sk-test-secret-value-1234"}', {}, None  # FAKE TEST KEY - DO NOT USE
        raise AssertionError(f"unexpected call: {method} {path}")

    result = get_or_create_tts_readiness_client(fake_http_request, "admin-token")

    assert result.ok is True
    assert result.client_id == "new-client"
    assert result.plan_code == "basic"
    assert result.temporary is True
    assert "suspended" not in result.detail
    assert "secret-value" not in result.detail
    assert ("POST", "/admin/clients") in calls


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_proxy_records_usage_on_201(mock_verify, tts_probe_setup):
    data = tts_probe_setup
    ac = data["ac"]
    sessionmaker = data["sessionmaker"]
    api_key = data["api_key"]
    client = data["client"]

    response_obj = httpx.Response(
        201,
        headers={"Content-Type": "audio/wav"},
        content=b"RIFF\x00\x00\x00\x00WAVEfmt ",
        request=httpx.Request("POST", "http://pocket-tts/tts"),
    )

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.request = AsyncMock(return_value=response_obj)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch("app.api.pocket_tts.httpx.AsyncClient", FakeAsyncClient):
        response = await ac.post(
            "/pocket-tts/tts",
            headers={"Authorization": f"Bearer {api_key}"},
            data={"text": "hello"},
        )

    assert response.status_code == 201

    async with sessionmaker() as session:
        events = (await session.execute(select(TtsUsageEvent).where(TtsUsageEvent.client_id == client.id))).scalars().all()
        assert len(events) == 1
        assert events[0].chars_input == 5
        assert events[0].api_key_prefix is not None

        counters = (await session.execute(select(QuotaCounter).where(QuotaCounter.client_id == client.id))).scalars().all()
        assert counters
        assert sum(counter.used_tts_chars for counter in counters) >= 10
