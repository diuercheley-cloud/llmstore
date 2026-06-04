import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multitenant_portal_isolation(admin_client: AsyncClient, admin_token_headers):
    # Setup Client A
    resp_a = await admin_client.post("/admin/clients", json={"name": "Client A"}, headers=admin_token_headers)
    client_a_id = resp_a.json()["id"]
    resp_key_a = await admin_client.post("/admin/api-keys", json={"client_id": client_a_id, "name": "Key A"}, headers=admin_token_headers)
    key_a = resp_key_a.json()["api_key"]

    # Setup Client B
    resp_b = await admin_client.post("/admin/clients", json={"name": "Client B"}, headers=admin_token_headers)
    client_b_id = resp_b.json()["id"]
    resp_key_b = await admin_client.post("/admin/api-keys", json={"client_id": client_b_id, "name": "Key B"}, headers=admin_token_headers)
    key_b = resp_key_b.json()["api_key"]

    # We can test that /portal/me returns the correct client
    me_resp_a = await admin_client.get("/portal/me", headers={"Authorization": f"Bearer {key_a}"})
    assert me_resp_a.status_code == 200
    assert me_resp_a.json()["id"] == client_a_id

    me_resp_b = await admin_client.get("/portal/me", headers={"Authorization": f"Bearer {key_b}"})
    assert me_resp_b.status_code == 200
    assert me_resp_b.json()["id"] == client_b_id

    # Cleanup
    await admin_client.delete(f"/admin/clients/{client_a_id}", headers=admin_token_headers)
    await admin_client.delete(f"/admin/clients/{client_b_id}", headers=admin_token_headers)
