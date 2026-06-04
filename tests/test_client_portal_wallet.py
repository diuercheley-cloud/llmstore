import json
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class FakeRedis:
    def __init__(self):
        self._store = {}

    async def ping(self):
        return True

    async def aclose(self):
        pass

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    async def incr(self, key):
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = val
        return val

    async def expire(self, key, seconds):
        return True

    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            deleted += int(key in self._store)
            self._store.pop(key, None)
        return deleted


@pytest_asyncio.fixture
async def app():
    from app.main import app as _app
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    fake_redis = FakeRedis()

    async def override_db():
        async with testing_session_local() as session:
            yield session

    _app.dependency_overrides[get_db_session] = override_db
    _app.dependency_overrides[get_redis] = lambda: fake_redis
    yield _app, testing_session_local, fake_redis
    _app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(app):
    _app, session_local, _redis = app
    async with session_local() as session:
        yield session


@pytest_asyncio.fixture
async def demo_client(app, db_session):
    from app.core.security import generate_api_key, hash_secret, short_prefix
    from app.models.api_key import ApiKey
    from app.models.client import Client

    client_obj = Client(name=f"portal-wallet-{uuid4().hex[:8]}")
    db_session.add(client_obj)
    await db_session.commit()
    await db_session.refresh(client_obj)

    token = generate_api_key()
    api_key = ApiKey(
        client_id=client_obj.id,
        name="test-key",
        key_prefix=short_prefix(token),
        key_hash=hash_secret(token),
        scopes_json=json.dumps([]),
    )
    db_session.add(api_key)
    await db_session.commit()
    return client_obj, token


@pytest_asyncio.fixture
async def portal_client(app, demo_client):
    _app, _session_local, _redis = app
    client_obj, token = demo_client
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app), base_url="http://testserver") as c:
        c.headers = {"Authorization": f"Bearer {token}"}
        yield c


@pytest.mark.asyncio
async def test_portal_wallet_shows_balance(portal_client, demo_client):
    client_obj, _ = demo_client
    resp = await portal_client.get("/portal/wallet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == str(client_obj.id)
    assert data["balance_brl"] == 0.0
    assert data["currency"] == "BRL"
    assert "available_brl" in data
    assert "pix_notice" in data


@pytest.mark.asyncio
async def test_portal_wallet_has_pix_notice(portal_client):
    resp = await portal_client.get("/portal/wallet")
    data = resp.json()
    assert "pix_notice" in data
    assert "não está disponível" in data["pix_notice"]


@pytest.mark.asyncio
async def test_portal_wallet_shows_transactions(portal_client):
    resp = await portal_client.get("/portal/wallet")
    data = resp.json()
    assert "transactions" in data
    assert isinstance(data["transactions"], list)


@pytest.mark.asyncio
async def test_portal_wallet_requires_auth(app):
    _app, _session_local, _redis = app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app), base_url="http://testserver") as c:
        resp = await c.get("/portal/wallet")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_portal_cannot_manual_credit(portal_client, demo_client):
    client_obj, _ = demo_client
    resp = await portal_client.post(
        f"/admin/billing/wallets/{client_obj.id}/manual-credit",
        json={"amount_brl": 100.0},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_portal_wallet_shows_estimated_consumption(portal_client):
    resp = await portal_client.get("/portal/wallet")
    data = resp.json()
    assert "consumption_estimate_brl" in data
    assert isinstance(data["consumption_estimate_brl"], float)
