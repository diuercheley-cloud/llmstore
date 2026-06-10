import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ops_center_endpoints_unauthorized(async_client: AsyncClient):
    endpoints = [
        "/admin/ops/overview",
        "/admin/ops/governance",
        "/admin/ops/risk",
        "/admin/ops/workflows",
        "/admin/ops/receipts",
        "/admin/ops/compliance",
        "/admin/ops/attestation"
    ]
    for endpoint in endpoints:
        response = await async_client.get(endpoint)
        assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"
