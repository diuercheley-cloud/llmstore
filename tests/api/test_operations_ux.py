import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_operations_overview(admin_client: AsyncClient):
    response = await admin_client.get(
        "/admin/operations/overview",
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "deployment_mode" in data
    assert "enterprise_features" in data


@pytest.mark.asyncio
async def test_get_operations_incidents(admin_client: AsyncClient):
    response = await admin_client.get(
        "/admin/operations/incidents",
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_reset_circuit_breaker_requires_write_permission(admin_client: AsyncClient):
    response = await admin_client.post(
        "/admin/operations/reset-circuit-breaker",
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_run_readiness(admin_client: AsyncClient):
    response = await admin_client.post(
        "/admin/operations/run-readiness",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"
