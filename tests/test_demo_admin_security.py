import re
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_demo_admin_security_unauthorized(admin_client: AsyncClient):
    response = await admin_client.get("/admin/demo/summary")
    assert response.status_code in (401, 403)

@pytest.mark.asyncio
async def test_demo_admin_security_no_api_keys(admin_client: AsyncClient, admin_token_headers: dict[str, str]):
    response = await admin_client.get(
        "/admin/demo/summary",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.text
    # Check that there are no exposed secrets looking like api keys (length 32+)
    # We should not see "api_key": "sk-..." with length > 20
    assert not re.search(r'"api_key":\s*"[a-zA-Z0-9_\-]{32,}"', data)
