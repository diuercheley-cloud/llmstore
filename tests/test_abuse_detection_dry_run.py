import os

os.environ["ABUSE_DETECTION_ENABLED"] = "true"
os.environ["ABUSE_DRY_RUN"] = "true"
os.environ["ABUSE_AUTO_SUSPEND_ENABLED"] = "false"

import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.client import Client
from app.services.security import record_abuse_event, suspend_client
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def dry_run_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield testing_session_local, fake_redis

    await engine.dispose()


@pytest.mark.asyncio
async def test_dry_run_does_not_suspend(dry_run_env):
    sessionmaker, fake_redis = dry_run_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        client = Client(id=client_id, name="dry-run-test")
        session.add(client)
        await session.commit()

    async with sessionmaker() as session:
        event, action = await record_abuse_event(
            session, fake_redis,
            signal="repeated_auth_errors",
            title="Dry run auth error test",
            client_id=client_id,
            details={"count": 10},
        )
        assert event is not None
        assert event.dry_run is True

        client = await session.get(Client, client_id)
        assert client is not None
        assert client.is_blocked is False


@pytest.mark.asyncio
async def test_suspend_client_manually_works(dry_run_env):
    sessionmaker, fake_redis = dry_run_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        client = Client(id=client_id, name="manual-suspend-test")
        session.add(client)
        await session.commit()

    async with sessionmaker() as session:
        result = await suspend_client(session, client_id, reason="manual test")
        assert result is not None
        assert result["action"] == "suspend_client"

        client = await session.get(Client, client_id)
        assert client.is_blocked is True


@pytest.mark.asyncio
async def test_auto_suspend_disabled_by_default(dry_run_env):
    sessionmaker, fake_redis = dry_run_env
    client_id = uuid.uuid4()

    assert os.environ.get("ABUSE_AUTO_SUSPEND_ENABLED") == "false"

    async with sessionmaker() as session:
        event, action = await record_abuse_event(
            session, fake_redis,
            signal="high_estimated_cost",
            title="Cost spike test",
            client_id=client_id,
        )
        assert action != "suspend_client"
