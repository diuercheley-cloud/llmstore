import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import uuid

@pytest_asyncio.fixture
async def client(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
def admin_headers():
    settings = get_settings()
    return {"X-Admin-Token": settings.admin_token}

@pytest.mark.asyncio
async def test_admin_lab_access(client: AsyncClient):
    response = await client.get("/admin-lab")
    assert response.status_code == 200
    assert "Admin Lab" in response.text
    assert "Clientes" in response.text
    assert "Planos" in response.text
    assert "Faturas" in response.text
    assert "Test Runner" in response.text


@pytest.mark.asyncio
async def test_admin_lab_disabled_in_public_exposure(client: AsyncClient):
    settings = get_settings()
    previous = settings.public_exposure
    settings.public_exposure = True
    try:
        response = await client.get("/admin-lab")
        assert response.status_code == 404
        assert response.json()["detail"] == "admin lab disabled in public exposure mode"

        static_response = await client.get("/static/admin-lab/index.html")
        assert static_response.status_code == 404
        assert static_response.json()["detail"] == "admin lab disabled in public exposure mode"
    finally:
        settings.public_exposure = previous

@pytest.mark.asyncio
async def test_soft_delete_client(client: AsyncClient, admin_headers: dict):
    # 1. Create client
    res = await client.post("/admin/clients", json={"name": "test-delete"}, headers=admin_headers)
    assert res.status_code == 201
    client_id = res.json()["id"]
    
    # 2. Soft delete
    res = await client.delete(f"/admin/clients/{client_id}", headers=admin_headers)
    assert res.status_code == 204
    
    # 3. Verify it doesn't appear in list
    res = await client.get("/admin/clients", headers=admin_headers)
    clients = res.json()
    assert not any(c["id"] == client_id for c in clients)

@pytest.mark.asyncio
async def test_cannot_delete_client_with_paid_invoice(client: AsyncClient, admin_headers: dict):
    # 1. Create client
    res = await client.post("/admin/clients", json={"name": "test-no-delete"}, headers=admin_headers)
    assert res.status_code == 201
    client_id = res.json()["id"]
    
    # 2. Create and pay invoice (simulated via mark-paid)
    res = await client.post("/admin/billing/invoices/generate", json={"client_id": client_id, "force": True}, headers=admin_headers)
    assert res.status_code == 201
    invoice_id = res.json()["created"][0]["id"]
    
    res = await client.patch(f"/admin/billing/invoices/{invoice_id}/mark-paid", json={"payment_method": "test"}, headers=admin_headers)
    assert res.status_code == 200
    
    # 3. Attempt delete
    res = await client.delete(f"/admin/clients/{client_id}", headers=admin_headers)
    assert res.status_code == 409
    assert "cannot delete client with paid invoices" in res.json()["detail"]

@pytest.mark.asyncio
async def test_mark_overdue(client: AsyncClient, admin_headers: dict):
    # 1. Create client and invoice
    res = await client.post("/admin/clients", json={"name": "test-overdue"}, headers=admin_headers)
    assert res.status_code == 201
    client_id = res.json()["id"]
    res = await client.post("/admin/billing/invoices/generate", json={"client_id": client_id, "force": True}, headers=admin_headers)
    assert res.status_code == 201
    invoice_id = res.json()["created"][0]["id"]
    
    # 2. Mark overdue
    res = await client.patch(f"/admin/billing/invoices/{invoice_id}/mark-overdue", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "overdue"


@pytest.mark.asyncio
async def test_create_and_cancel_payment(client: AsyncClient, admin_headers: dict):
    res = await client.post("/admin/clients", json={"name": "test-payment"}, headers=admin_headers)
    assert res.status_code == 201
    client_id = res.json()["id"]

    res = await client.post("/admin/billing/invoices/generate", json={"client_id": client_id, "force": True}, headers=admin_headers)
    assert res.status_code == 201
    invoice_id = res.json()["created"][0]["id"]

    res = await client.post(
        "/admin/billing/payments",
        json={"invoice_id": invoice_id, "amount": 12.5, "payment_method": "manual_pix"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    payment_id = res.json()["id"]

    res = await client.patch(f"/admin/billing/payments/{payment_id}/cancel", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_patch_billing_plan(client: AsyncClient, admin_headers: dict):
    res = await client.post(
        "/admin/billing/plans",
        json={
            "code": "lab-plan",
            "name": "Lab Plan",
            "description": "for admin lab",
            "rate_limit_per_minute": 12,
            "daily_token_quota": 12000,
            "monthly_token_quota": 120000,
            "weekly_token_quota": 60000,
            "max_output_tokens": 512,            "allow_streaming": True,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    plan_id = res.json()["id"]

    res = await client.patch(
        f"/admin/billing/plans/{plan_id}",
        json={"name": "Lab Plan Updated", "is_active": False},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Lab Plan Updated"
    assert res.json()["is_active"] is False

@pytest.mark.asyncio
async def test_test_runner_protection(client: AsyncClient, admin_headers: dict):
    # By default, TEST_TOOLS_ENABLED is False in Settings
    res = await client.get("/admin/test/commands", headers=admin_headers)
    assert res.status_code == 403
