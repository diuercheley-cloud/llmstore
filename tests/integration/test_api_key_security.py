import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_client_id(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Security Test Client", "rate_limit_per_minute": 10}
    )
    return resp.json()["id"]

@pytest.mark.asyncio
async def test_api_key_ip_restriction(admin_client: AsyncClient, admin_token_headers, test_client_id):
    # Create key restricted to a specific IP
    create_resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={
            "client_id": test_client_id,
            "name": "IP Key",
            "allowed_ips": ["1.2.3.4"]
        }
    )
    api_key = create_resp.json()["api_key"]

    # Try to use it (default test client IP is usually 127.0.0.1 or 'testclient')
    # The middleware sets request.state.source_ip
    usage_resp = await admin_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "unsloth/gemma-4-E4B-it-GGUF",
            "messages": [{"role": "user", "content": "Hi"}]
        }
    )
    assert usage_resp.status_code == 403
    assert "not allowed for this API key" in usage_resp.json()["detail"]

@pytest.mark.asyncio
async def test_api_key_no_plaintext_storage(admin_client: AsyncClient, admin_token_headers, test_client_id):
    # This is more of a logic check since we can't easily peek into the DB here 
    # but we can verify that listing keys never returns the full key.
    await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": test_client_id, "name": "Secret Key"}
    )
    
    list_resp = await admin_client.get("/admin/api-keys", headers=admin_token_headers)
    for key in list_resp.json():
        assert "api_key" not in key
        assert "key_hash" not in key # Should also not return hash
        assert "key_prefix" in key
        assert len(key["key_prefix"]) <= 12
