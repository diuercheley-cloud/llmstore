import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def portal_client_data(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Portal Test Client", "rate_limit_per_minute": 10}
    )
    client_data = resp.json()
    client_id = client_data["id"]
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Portal Test Key"}
    )
    key_data = resp.json()
    return {"id": client_id, "api_key": key_data["api_key"]}

@pytest.mark.asyncio
async def test_portal_me(admin_client: AsyncClient, portal_client_data):
    response = await admin_client.get(
        "/portal/me",
        headers={"Authorization": f"Bearer {portal_client_data['api_key']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == portal_client_data["id"]
    assert "plan" in data

@pytest.mark.asyncio
async def test_portal_models(admin_client: AsyncClient, portal_client_data):
    response = await admin_client.get(
        "/portal/models",
        headers={"Authorization": f"Bearer {portal_client_data['api_key']}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
