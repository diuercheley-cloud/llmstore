import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_responses_api_auth_required(admin_client: AsyncClient):
    resp = await admin_client.post("/v1/responses", json={
        "model": "default",
        "input": "hi"
    })
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_responses_api_suspended_client(admin_client: AsyncClient, admin_token_headers):
    # 1. Create a client
    resp = await admin_client.post("/admin/clients", json={
        "name": "suspended-client",
        "description": "test",
        "rate_limit_per_minute": 10
    }, headers=admin_token_headers)
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # Suspend client
    resp = await admin_client.patch(f"/admin/clients/{client_id}", json={
        "billing_status": "suspended"
    }, headers=admin_token_headers)
    assert resp.status_code == 200

    # 2. Create an API key
    resp = await admin_client.post("/admin/api-keys", json={
        "client_id": client_id,
        "name": "suspended-key"
    }, headers=admin_token_headers)
    assert resp.status_code == 201
    api_key = resp.json()["api_key"]

    # 3. Call /v1/responses
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await admin_client.post("/v1/responses", json={
        "model": "default",
        "input": "hi"
    }, headers=headers)
    assert resp.status_code == 402
