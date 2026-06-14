import pytest


@pytest.mark.asyncio
async def test_aiops_recommendations_endpoint(async_client, admin_token_headers):
    response = await async_client.get(
        "/admin/aiops/recommendations",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
