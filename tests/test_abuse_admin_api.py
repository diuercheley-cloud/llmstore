import os

os.environ["ABUSE_DETECTION_ENABLED"] = "true"
os.environ["ABUSE_DRY_RUN"] = "true"
os.environ["ABUSE_AUTO_SUSPEND_ENABLED"] = "false"

import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.client import Client
from app.services.security import record_abuse_event
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def admin_abuse_env(isolated_db_url, fake_redis):
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
async def test_admin_abuse_events_requires_token(admin_abuse_env):
    ac, _, _ = admin_abuse_env
    resp = await ac.get("/admin/security/abuse/events")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_abuse_events_with_token(admin_abuse_env):
    ac, sessionmaker, fake_redis = admin_abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="requests_per_minute_above_plan",
            title="API Test Event",
            client_id=client_id,
        )

    headers = {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    resp = await ac.get("/admin/security/abuse/events", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_admin_abuse_summary(admin_abuse_env):
    ac, sessionmaker, fake_redis = admin_abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="cloud_without_balance",
            title="Summary Test",
            client_id=client_id,
        )

    headers = {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    resp = await ac.get("/admin/security/abuse/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "by_signal" in data
    assert "dry_run" in data
    assert data["dry_run"] is True
    assert data["auto_suspend_enabled"] is False
    assert data["detection_enabled"] is True


@pytest.mark.asyncio
async def test_admin_abuse_events_filter_by_signal(admin_abuse_env):
    ac, sessionmaker, fake_redis = admin_abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        await record_abuse_event(
            session, fake_redis,
            signal="repeated_auth_errors",
            title="Auth Error Event",
            client_id=client_id,
        )
        await record_abuse_event(
            session, fake_redis,
            signal="cloud_without_balance",
            title="Cloud Balance Event",
            client_id=client_id,
        )

    headers = {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    resp = await ac.get(
        "/admin/security/abuse/events?signal=repeated_auth_errors",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    for event in data:
        assert event["signal"] == "repeated_auth_errors"


@pytest.mark.asyncio
async def test_admin_abuse_suspend_client(admin_abuse_env):
    ac, sessionmaker, fake_redis = admin_abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        client = Client(id=client_id, name="suspend-api-test")
        session.add(client)
        await session.commit()

    headers = {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    resp = await ac.post(
        f"/admin/security/abuse/clients/{client_id}/suspend?reason=api%20test",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "suspend_client"

    async with sessionmaker() as session:
        client = await session.get(Client, client_id)
        assert client.is_blocked is True


@pytest.mark.asyncio
async def test_admin_abuse_unsuspend_client(admin_abuse_env):
    ac, sessionmaker, fake_redis = admin_abuse_env
    client_id = uuid.uuid4()

    async with sessionmaker() as session:
        client = Client(id=client_id, name="unsuspend-api-test", is_blocked=True)
        session.add(client)
        await session.commit()

    headers = {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    resp = await ac.post(
        f"/admin/security/abuse/clients/{client_id}/unsuspend?reason=api%20test",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "unsuspend"

    async with sessionmaker() as session:
        client = await session.get(Client, client_id)
        assert client.is_blocked is False
