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
    import app.core.config
    settings = app.core.config.get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    resp = await admin_client.get("/portal/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["demo_mode"] is True
    assert data["name"] == "Test Demo Client"

async def test_demo_mode_inactive(admin_client: AsyncClient, demo_client_fixture: dict, monkeypatch):
    import app.core.config
    settings = app.core.config.get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)

    headers = {"Authorization": f"Bearer {demo_client_fixture['api_key']}"}
    resp = await admin_client.get("/portal/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["demo_mode"] is False
