import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

@pytest_asyncio.fixture
async def test_client_id(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Auth Test Client", "rate_limit_per_minute": 10}
    )
    return resp.json()["id"]

@pytest.mark.asyncio
async def test_auth_valid_key(admin_client: AsyncClient, admin_token_headers, test_client_id):
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Valid Key"}
    )
    api_key = create_resp.json()["api_key"]
    
    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_auth_expired_key(admin_client: AsyncClient, admin_token_headers, test_client_id):
    # Expired 1 hour ago
    expired_dt = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={
            "client_id": test_client_id, 
            "name": "Expired Key",
            "expires_at": expired_dt
        }
    )
    api_key = create_resp.json()["api_key"]
    
    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_auth_revoked_key(admin_client: AsyncClient, admin_token_headers, test_client_id):
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Revoke Me"}
    )
    api_key = create_resp.json()["api_key"]
    key_id = create_resp.json()["id"]
    
    # Revoke it
    await admin_client.delete(f"/admin/api-keys/{key_id}", headers=admin_token_headers)
    
    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 401
    assert "invalid api key" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_auth_last_used_at_updates(admin_client: AsyncClient, admin_token_headers, test_client_id):
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Usage Key"}
    )
    api_key = create_resp.json()["api_key"]
    key_id = create_resp.json()["id"]
    
    # Initial state
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    key_info = next(k for k in list_resp.json() if k["id"] == key_id)
    assert key_info["last_used_at"] is None
    
    # Use it
    await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    
    # Check updated
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    key_info = next(k for k in list_resp.json() if k["id"] == key_id)
    assert key_info["last_used_at"] is not None
