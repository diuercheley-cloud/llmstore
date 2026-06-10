import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_local_billing_cycle(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.post(
        "/admin/billing/run-cycle",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "generated_at" in data
    assert "created_count" in data
    assert "updated_count" in data
    assert "skipped_count" in data
    assert "reason" in data
