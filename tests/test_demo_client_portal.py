import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def demo_client_fixture(admin_client: AsyncClient, admin_token_headers):
    # Create client
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Test Demo Client", "rate_limit_per_minute": 10}
    )
    client_data = resp.json()
    client_id = client_data["id"]

    # Create API key
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Demo Key"}
    )
    key_data = resp.json()

    return {"client": client_data, "api_key": key_data["api_key"]}

async def test_demo_mode_active(admin_client: AsyncClient, demo_client_fixture: dict, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    resp = await admin_client.get("/portal/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["demo_mode"] is True
    assert data["name"] == "Test Demo Client"

async def test_demo_mode_inactive(admin_client: AsyncClient, demo_client_fixture: dict, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    resp = await admin_client.get("/portal/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["demo_mode"] is False

async def test_portal_endpoints_with_demo_client(admin_client: AsyncClient, demo_client_fixture: dict, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    
    # Test /portal/usage
    resp = await admin_client.get("/portal/usage", headers=headers)
    assert resp.status_code == 200
    usage_data = resp.json()
    assert "daily_usage" in usage_data
    assert "monthly_usage" in usage_data
    
    # Test /portal/models
    resp = await admin_client.get("/portal/models", headers=headers)
    assert resp.status_code == 200
    models_data = resp.json()
    assert isinstance(models_data, list)
    
    # Test /portal/invoices
    resp = await admin_client.get("/portal/invoices", headers=headers)
    assert resp.status_code == 200
    invoices_data = resp.json()
    assert "invoices" in invoices_data
    
    # Test /client/rag/documents
    resp = await admin_client.get("/client/rag/documents", headers=headers)
    assert resp.status_code == 200
    rag_data = resp.json()
    assert "data" in rag_data

async def test_portal_test_chat_auth(admin_client: AsyncClient, demo_client_fixture: dict, monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    
    # Test /portal/test-chat
    # We don't need a real backend for this test if we just want to check auth and basic flow
    # but we might need to mock the inference proxy if we want it to "work"
    # For now, let's just check it reaches the endpoint logic
    payload = {"prompt": "Hello", "model": "default", "max_tokens": 10}
    resp = await admin_client.post("/portal/test-chat", headers=headers, json=payload)
    
    # It might fail with 500 or 503 if no models are registered, but shouldn't be 401
    assert resp.status_code != 401
    assert resp.status_code != 403
