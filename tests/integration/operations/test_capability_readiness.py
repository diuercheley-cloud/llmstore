import pytest
import pytest_asyncio
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def readiness_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_capability_readiness_endpoints(
    readiness_client: AsyncClient, admin_token_headers: dict
):
    capabilities = [
        "agent-runtime",
        "stateful-workflows",
        "agent-iam",
        "saas-connectors",
        "graphrag",
        "observability",
        "tool-execution",
        "memory-governance",
    ]

    for cap in capabilities:
        response = await readiness_client.get(
            f"/admin/readiness/{cap}", headers=admin_token_headers
        )
        # Should be 200 if ready, or 503 if not ready but endpoint exists
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert data["capability"] == cap
            assert "status" in data


@pytest.mark.asyncio
async def test_capability_readiness_unauthorized(readiness_client: AsyncClient):
    response = await readiness_client.get("/admin/readiness/agent-runtime")
    assert response.status_code == 401
