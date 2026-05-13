import os

os.environ["ABUSE_DETECTION_ENABLED"] = "true"
os.environ["ABUSE_DRY_RUN"] = "true"
os.environ["ABUSE_AUTO_SUSPEND_ENABLED"] = "false"

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.security import record_abuse_event, list_abuse_events


@pytest_asyncio.fixture
async def security_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield testing_session_local, fake_redis

    await engine.dispose()


@pytest.mark.asyncio
async def test_no_full_prompts_in_events(security_env):
    sessionmaker, fake_redis = security_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="repeated_giant_prompts",
            title="Test event",
            client_id=client_id,
            details={
                "prompt_tokens": 4096,
                "repetitions": 3,
            },
        )

    async with sessionmaker() as session:
        events = await list_abuse_events(session)
        for event in events:
            details = event.get("details", {})
            raw = str(details)
            assert "sk-" not in raw, "API key found in event details"
            prefix = event.get("api_key_prefix") or ""
            assert "sk-" not in prefix, "API key prefix leaks full key"
            content = str(event.get("title", "")) + str(details)
            assert "Bearer" not in content, "Bearer token leaked in event"
            assert "Authorization" not in content, "Authorization header leaked"


@pytest.mark.asyncio
async def test_no_api_keys_in_details(security_env):
    sessionmaker, fake_redis = security_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="cloud_without_balance",
            title="Security test",
            client_id=client_id,
            details={"wallet_balance_brl": 0.0},
        )

    async with sessionmaker() as session:
        events = await list_abuse_events(session)
        for event in events:
            event_str = str(event)
            assert "api_key" not in event_str.lower() or "api_key_prefix" not in str(event.get("details", {})), \
                "Full API key leaked in event response"


@pytest.mark.asyncio
async def test_no_secrets_in_summary(security_env):
    sessionmaker, fake_redis = security_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="requests_per_minute_above_plan",
            title="Secret check",
            client_id=client_id,
        )

    async with sessionmaker() as session:
        from app.services.security import get_abuse_summary
        summary = await get_abuse_summary(session)
        summary_str = str(summary)
        assert "sk-" not in summary_str
        assert "secret" not in summary_str.lower() or "no_secret" in summary_str.lower()


@pytest.mark.asyncio
async def test_abuse_detection_enabled_by_default():
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.abuse_detection_enabled is True


@pytest.mark.asyncio
async def test_auto_suspend_disabled_by_default():
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.abuse_auto_suspend_enabled is False


@pytest.mark.asyncio
async def test_dry_run_enabled_by_default():
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.abuse_dry_run is True
