import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_basic(admin_client: AsyncClient):
    response = await admin_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["process"] == "alive"


@pytest.mark.asyncio
async def test_ready_structure(admin_client: AsyncClient):
    response = await admin_client.get("/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "postgres" in data["dependencies"]
    assert "redis" in data["dependencies"]
    assert "migrations" in data["dependencies"]
