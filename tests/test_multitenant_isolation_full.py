import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_multitenant_isolation_full(admin_client: AsyncClient, admin_token_headers):
    # Setup Client A
    resp_a = await admin_client.post(
        "/admin/clients", 
        json={"name": "Client A", "description": "Isol A"},
        headers=admin_token_headers
    )
    assert resp_a.status_code == 201
    client_a_id = resp_a.json()["id"]

    resp_key_a = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_a_id, "name": "Key A"},
        headers=admin_token_headers
    )
    assert resp_key_a.status_code == 201
    key_a = resp_key_a.json()["api_key"]

    # Setup Client B
    resp_b = await admin_client.post(
        "/admin/clients", 
        json={"name": "Client B", "description": "Isol B"},
        headers=admin_token_headers
    )
    assert resp_b.status_code == 201
    client_b_id = resp_b.json()["id"]

    resp_key_b = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_b_id, "name": "Key B"},
        headers=admin_token_headers
    )
    assert resp_key_b.status_code == 201
    key_b = resp_key_b.json()["api_key"]

    # Client A accesses its own portal (using key A)
    chat_resp_a = await admin_client.post(
        "/v1/chat/completions",
        json={"model": "test-model", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {key_a}"}
    )
    
    # For Admin, ensure standard tokens don't work for PATCH which exists
    admin_fail = await admin_client.patch(
        f"/admin/clients/{client_b_id}",
        json={"description": "hacked"},
        headers={"Authorization": f"Bearer {key_a}"}
    )
    assert admin_fail.status_code in (401, 403)

    # Cleanup
    await admin_client.delete(f"/admin/clients/{client_a_id}", headers=admin_token_headers)
    await admin_client.delete(f"/admin/clients/{client_b_id}", headers=admin_token_headers)
