import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def portal_client_data(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Portal Test Client", "rate_limit_per_minute": 10},
    )
    client_data = resp.json()
    client_id = client_data["id"]
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Portal Test Key"},
    )
    key_data = resp.json()
    return {"id": client_id, "api_key": key_data["api_key"]}


@pytest.mark.asyncio
async def test_manage_api_keys(admin_client: AsyncClient, portal_client_data):
    client_id = portal_client_data["id"]
    client_api_key = portal_client_data["api_key"]

    # List
    list_resp = await admin_client.get(
        "/portal/api-keys", headers={"Authorization": f"Bearer {client_api_key}"}
    )
    assert list_resp.status_code == 200

    # Create
    create_resp = await admin_client.post(
        "/portal/api-keys",
        headers={"Authorization": f"Bearer {client_api_key}"},
        json={"client_id": client_id, "name": "New Portal Key"},
    )
    assert create_resp.status_code == 201
    new_key = create_resp.json()["api_key"]
    new_key_id = create_resp.json()["id"]

    # Use
    me_resp = await admin_client.get("/portal/me", headers={"Authorization": f"Bearer {new_key}"})
    assert me_resp.status_code == 200

    # Revoke
    revoke_resp = await admin_client.delete(
        f"/portal/api-keys/{new_key_id}", headers={"Authorization": f"Bearer {client_api_key}"}
    )
    assert revoke_resp.status_code == 200

    # Verify
    me_resp_revoked = await admin_client.get(
        "/portal/me", headers={"Authorization": f"Bearer {new_key}"}
    )
    assert me_resp_revoked.status_code == 401
