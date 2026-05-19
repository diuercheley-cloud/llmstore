import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_operations_overview(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/admin/operations/overview",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "deployment_mode" in data
    assert "enterprise_features" in data

@pytest.mark.asyncio
async def test_get_operations_incidents(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/admin/operations/incidents",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_reset_circuit_breaker_requires_write_permission(client: AsyncClient, admin_read_token: str):
    response = await client.post(
        "/admin/operations/reset-circuit-breaker",
        headers={"X-Admin-Token": admin_read_token}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_run_readiness(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/admin/operations/run-readiness",
        headers={"X-Admin-Token": admin_token}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"
