import os
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.db.session import get_db_session


@pytest_asyncio.fixture
async def app():
    from app.main import app as _app
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db():
        async with testing_session_local() as session:
            yield session

    _app.dependency_overrides[get_db_session] = override_db
    yield _app
    _app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}


@pytest_asyncio.fixture
async def demo_client_id(client, admin_headers):
    name = f"wallet-test-{uuid4().hex[:8]}"
    resp = await client.post("/admin/clients", json={"name": name}, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_admin_list_wallets(client, admin_headers):
    resp = await client.get("/admin/billing/wallets", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_list_wallets_requires_auth(client):
    resp = await client.get("/admin/billing/wallets")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_get_wallet_creates_if_not_exists(client, admin_headers, demo_client_id):
    resp = await client.get(f"/admin/billing/wallets/{demo_client_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == demo_client_id
    assert data["balance_brl"] == 0.0
    assert data["currency"] == "BRL"


@pytest.mark.asyncio
async def test_admin_manual_credit_increases_balance(client, admin_headers, demo_client_id):
    resp = await client.post(
        f"/admin/billing/wallets/{demo_client_id}/manual-credit",
        json={"amount_brl": 150.0, "reason": "test credit"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    tx = resp.json()
    assert tx["type"] == "manual_credit"
    assert tx["amount_brl"] == 150.0

    resp2 = await client.get(f"/admin/billing/wallets/{demo_client_id}", headers=admin_headers)
    assert resp2.json()["balance_brl"] == 150.0


@pytest.mark.asyncio
async def test_admin_adjustment(client, admin_headers, demo_client_id):
    await client.post(
        f"/admin/billing/wallets/{demo_client_id}/manual-credit",
        json={"amount_brl": 100.0},
        headers=admin_headers,
    )
    resp = await client.post(
        f"/admin/billing/wallets/{demo_client_id}/adjustment",
        json={"amount_brl": -30.0, "reason": "fee adjustment"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "adjustment"
    assert data["amount_brl"] == -30.0


@pytest.mark.asyncio
async def test_admin_adjustment_negative_balance_blocked(client, admin_headers, demo_client_id):
    resp = await client.post(
        f"/admin/billing/wallets/{demo_client_id}/adjustment",
        json={"amount_brl": -50.0},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_transactions_list(client, admin_headers, demo_client_id):
    await client.post(
        f"/admin/billing/wallets/{demo_client_id}/manual-credit",
        json={"amount_brl": 50.0, "reason": "tx list test"},
        headers=admin_headers,
    )
    resp = await client.get(f"/admin/billing/wallets/{demo_client_id}/transactions", headers=admin_headers)
    assert resp.status_code == 200
    txs = resp.json()
    assert len(txs) >= 1
    assert txs[0]["type"] == "manual_credit"


@pytest.mark.asyncio
async def test_manual_credit_requires_admin_token(client, demo_client_id):
    resp = await client.post(
        f"/admin/billing/wallets/{demo_client_id}/manual-credit",
        json={"amount_brl": 100.0},
    )
    assert resp.status_code in (401, 403)
