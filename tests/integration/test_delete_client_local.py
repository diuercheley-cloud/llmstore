import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def temp_client(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": f"Delete Test {uuid.uuid4().hex[:6]}", "description": "Temp client"},
    )
    return resp.json()


@pytest.mark.asyncio
async def test_purge_client_anonymize(admin_client: AsyncClient, admin_token_headers, temp_client):
    client_id = temp_client["id"]

    # Create an API key to verify it gets revoked
    key_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "test-key"},
    )
    key_id = key_resp.json()["id"]

    # Purge with anonymize
    resp = await admin_client.post(
        f"/admin/clients/{client_id}/purge",
        headers=admin_token_headers,
        json={"anonymize_instead": True},
    )
    assert resp.status_code == 204

    # Verify client is not in active list
    list_resp = await admin_client.get("/admin/clients", headers=admin_token_headers)
    assert not any(c["id"] == client_id for c in list_resp.json())

    # Verify API key is revoked
    keys_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    key = next(k for k in keys_resp.json() if k["id"] == key_id)
    assert key["is_active"] is False
    assert key["revoked_at"] is not None


@pytest.mark.asyncio
async def test_purge_client_full_delete(
    admin_client: AsyncClient, admin_token_headers, temp_client
):
    client_id = temp_client["id"]

    # Purge with full delete
    resp = await admin_client.post(
        f"/admin/clients/{client_id}/purge",
        headers=admin_token_headers,
        json={"delete_invoices": True, "anonymize_instead": False},
    )
    assert resp.status_code == 204

    # Verify client is gone from active list
    list_resp = await admin_client.get("/admin/clients", headers=admin_token_headers)
    assert not any(c["id"] == client_id for c in list_resp.json())


@pytest.mark.asyncio
async def test_purge_demo_client_safety(admin_client: AsyncClient, admin_token_headers):
    # Create demo-client first
    await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "demo-client", "description": "Demo client"},
    )

    # Find demo-client
    list_resp = await admin_client.get("/admin/clients", headers=admin_token_headers)
    demo_client = next(c for c in list_resp.json() if c["name"] == "demo-client")
    demo_id = demo_client["id"]

    # Try to purge without allow_demo_client
    resp = await admin_client.post(
        f"/admin/clients/{demo_id}/purge",
        headers=admin_token_headers,
        json={"anonymize_instead": True, "allow_demo_client": False},
    )
    assert resp.status_code == 403
    assert "cannot purge demo client" in resp.json()["detail"]
