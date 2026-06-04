from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_client_id(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Lifecycle Test Client", "rate_limit_per_minute": 10}
    )
    return resp.json()["id"]

@pytest.mark.asyncio
async def test_api_key_full_lifecycle(admin_client: AsyncClient, admin_token_headers, test_client_id):
    # 1. Create
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={
            "client_id": test_client_id,
            "name": "Life Key",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
    )
    assert create_resp.status_code == 201
    key_data = create_resp.json()
    api_key = key_data["api_key"]
    key_id = key_data["id"]
    assert key_data["name"] == "Life Key"
    assert "sk-local-" in api_key
    assert key_data["expires_at"] is not None

    # 2. List
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    my_key = next(k for k in keys if k["id"] == key_id)
    assert my_key["name"] == "Life Key"
    assert "api_key" not in my_key # Should not return plaintext key in list
    assert my_key["is_active"] is True

    # 3. Rotate
    rotate_resp = await admin_client.post(
        f"/admin/api-keys/{key_id}/rotate",
        headers=admin_token_headers
    )
    assert rotate_resp.status_code == 200
    rotate_data = rotate_resp.json()
    new_api_key = rotate_data["api_key"]["api_key"]
    assert new_api_key != api_key
    
    # 4. Verify old is revoked
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    old_key = next(k for k in list_resp.json() if k["id"] == key_id)
    assert old_key["revoked_at"] is not None
    assert old_key["is_active"] is False

    # 5. Revoke new
    new_key_id = rotate_data["api_key"]["id"]
    revoke_resp = await admin_client.delete(
        f"/admin/api-keys/{new_key_id}",
        headers=admin_token_headers
    )
    assert revoke_resp.status_code == 204

    # 6. Verify new is revoked
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    revoked_key = next(k for k in list_resp.json() if k["id"] == new_key_id)
    assert revoked_key["revoked_at"] is not None
    assert revoked_key["is_active"] is False
