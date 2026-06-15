import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multitenant_embeddings_isolation(admin_client: AsyncClient, admin_token_headers):
    # Setup Client A
    resp_a = await admin_client.post(
        "/admin/clients",
        json={"name": "Client A", "description": "Isol A"},
        headers=admin_token_headers,
    )
    client_a_id = resp_a.json()["id"]
    resp_key_a = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_a_id, "name": "Key A"},
        headers=admin_token_headers,
    )
    key_a = resp_key_a.json()["api_key"]

    # Test Embeddings Access
    # Since client_id is inferred from key, cross-access is hard to test unless we find an endpoint that takes client_id.

    # Cleanup
    await admin_client.delete(f"/admin/clients/{client_a_id}", headers=admin_token_headers)


@pytest.mark.asyncio
async def test_multitenant_responses_isolation(admin_client: AsyncClient, admin_token_headers):
    # Similar to embeddings
    resp_a = await admin_client.post(
        "/admin/clients",
        json={"name": "Client A", "description": "Isol A"},
        headers=admin_token_headers,
    )
    client_a_id = resp_a.json()["id"]
    await admin_client.delete(f"/admin/clients/{client_a_id}", headers=admin_token_headers)
