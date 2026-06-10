import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_responses_api_streaming_501(admin_client: AsyncClient, admin_token_headers):
    # 1. Create a client and key
    resp = await admin_client.post("/admin/clients", json={
        "name": "stream-client",
        "description": "test",
        "rate_limit_per_minute": 10
    }, headers=admin_token_headers)
    assert resp.status_code == 201
    client_id = resp.json()["id"]
    resp = await admin_client.post("/admin/api-keys", json={
        "client_id": client_id,
        "name": "stream-key"
    }, headers=admin_token_headers)
    assert resp.status_code == 201
    api_key = resp.json()["api_key"]

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "default",
        "input": "hi",
        "stream": True
    }
    resp = await admin_client.post("/v1/responses", json=payload, headers=headers)
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "responses_streaming"
