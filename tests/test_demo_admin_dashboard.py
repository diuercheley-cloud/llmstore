import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_demo_admin_summary(admin_client: AsyncClient, admin_token_headers: dict[str, str]):
    response = await admin_client.get(
        "/admin/demo/summary",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "demo_enabled" in data
    assert "demo_client" in data
    assert "demo_usage" in data
    assert "demo_billing" in data
    assert "demo_rag" in data
    assert "demo_models" in data
    assert "warnings" in data
