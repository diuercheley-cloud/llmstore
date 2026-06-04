import os
import uuid

os.environ["ABUSE_DETECTION_ENABLED"] = "true"
os.environ["ABUSE_DRY_RUN"] = "true"
os.environ["ABUSE_AUTO_SUSPEND_ENABLED"] = "false"


import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.services.security import (
    check_auth_error_burst,
    check_cache_miss_abuse,
    check_cloud_without_balance,
    check_cost_spike,
    check_rate_limit_abuse,
    check_repeated_giant_prompt,
    check_request_loop,
    get_abuse_summary,
    list_abuse_events,
    record_abuse_event,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def abuse_env(isolated_db_url, fake_redis):
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
        yield ac, testing_session_local, fake_redis

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_abuse_event(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        event, action = await record_abuse_event(
            session, fake_redis,
            signal="requests_per_minute_above_plan",
            title="Test event",
            client_id=client_id,
            details={"count": 10},
        )
        assert event is not None
        assert event.signal == "requests_per_minute_above_plan"
        assert event.dry_run is True
        assert action == "warn"


@pytest.mark.asyncio
async def test_list_abuse_events(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="requests_per_minute_above_plan",
            title="Event 1",
            client_id=client_id,
        )
        await record_abuse_event(
            session, fake_redis,
            signal="cloud_without_balance",
            title="Event 2",
            client_id=client_id,
        )

    async with sessionmaker() as session:
        events = await list_abuse_events(session)
        assert len(events) >= 2


@pytest.mark.asyncio
async def test_get_abuse_summary(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="requests_per_minute_above_plan",
            title="Test",
            client_id=client_id,
        )

    async with sessionmaker() as session:
        summary = await get_abuse_summary(session)
        assert summary["total_events"] >= 1
        assert summary["dry_run"] is True
        assert summary["auto_suspend_enabled"] is False
        assert summary["detection_enabled"] is True


@pytest.mark.asyncio
async def test_check_rate_limit_abuse(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        action = await check_rate_limit_abuse(
            session, fake_redis,
            client_id=client_id,
            limit_per_minute=5,
            current_count=10,
        )
        assert action is not None

    async with sessionmaker() as session:
        action = await check_rate_limit_abuse(
            session, fake_redis,
            client_id=client_id,
            limit_per_minute=10,
            current_count=5,
        )
        assert action is None


@pytest.mark.asyncio
async def test_check_cloud_without_balance(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        action = await check_cloud_without_balance(
            session, fake_redis,
            client_id=client_id,
            wallet_balance_brl=0.0,
        )
        assert action is not None

    async with sessionmaker() as session:
        action = await check_cloud_without_balance(
            session, fake_redis,
            client_id=client_id,
            wallet_balance_brl=50.0,
        )
        assert action is None


@pytest.mark.asyncio
async def test_check_cost_spike(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        action = await check_cost_spike(
            session, fake_redis,
            client_id=client_id,
            recent_cost_brl=10.0,
        )
        assert action is not None

    async with sessionmaker() as session:
        action = await check_cost_spike(
            session, fake_redis,
            client_id=client_id,
            recent_cost_brl=1.0,
        )
        assert action is None


@pytest.mark.asyncio
async def test_check_auth_error_burst(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    source_ip = "192.168.1.100"

    async with sessionmaker() as session:
        action = None
        for _ in range(5):
            action = await check_auth_error_burst(
                session, fake_redis,
                source_ip=source_ip,
            )
        assert action is not None


@pytest.mark.asyncio
async def test_check_request_loop(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()
    fingerprint = "abc123def456"

    async with sessionmaker() as session:
        action = None
        for _ in range(5):
            action = await check_request_loop(
                session, fake_redis,
                client_id=client_id,
                fingerprint=fingerprint,
            )
        assert action is not None


@pytest.mark.asyncio
async def test_check_repeated_giant_prompt(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()
    fp = "bigpromptfingerprint"

    async with sessionmaker() as session:
        action = await check_repeated_giant_prompt(
            session, fake_redis,
            client_id=client_id,
            prompt_tokens=500,
            prompt_fingerprint=fp,
        )
        assert action is None

        action = None
        for _ in range(3):
            action = await check_repeated_giant_prompt(
                session, fake_redis,
                client_id=client_id,
                prompt_tokens=4096,
                prompt_fingerprint=fp,
            )
        assert action is not None


@pytest.mark.asyncio
async def test_check_cache_miss_abuse(abuse_env):
    _, sessionmaker, fake_redis = abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        action = await check_cache_miss_abuse(
            session, fake_redis,
            client_id=client_id,
            cache_hits=1,
            cache_misses=10,
        )
        assert action is not None

    async with sessionmaker() as session:
        action = await check_cache_miss_abuse(
            session, fake_redis,
            client_id=client_id,
            cache_hits=10,
            cache_misses=1,
        )
        assert action is None


@pytest.mark.asyncio
async def test_all_signals_registered():
    from app.services.security.abuse_detection import ABUSE_SIGNALS
    expected_signals = [
        "requests_per_minute_above_plan",
        "tokens_per_minute_above_plan",
        "repeated_auth_errors",
        "repeated_giant_prompts",
        "request_loop",
        "high_cache_miss_repetitive",
        "cloud_without_balance",
        "high_estimated_cost",
        "repeated_streaming_abort",
        "excessive_rag_upload",
        "excessive_tts_chars",
    ]
    for signal in expected_signals:
        assert signal in ABUSE_SIGNALS, f"Missing signal: {signal}"
    assert len(ABUSE_SIGNALS) == len(expected_signals)
