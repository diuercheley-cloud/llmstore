import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_config_effective_endpoint(async_client: AsyncClient):
    # The admin_token is defined in conftest.py as "test-admin-token"
    # We use X-Admin-Token header as per middleware.py
    response = await async_client.get(
        "/admin/config/effective", headers={"X-Admin-Token": "test-admin-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Check for secret redaction
    for item in data:
        key = item["key"].upper()
        if any(p in key for p in ["KEY", "PASSWORD", "SECRET", "TOKEN"]):
            if item["value"] is not None and item["value"] != "":
                assert item["value"] == "********"


@pytest.mark.asyncio
async def test_admin_config_detailed_endpoint(async_client: AsyncClient):
    response = await async_client.get(
        "/admin/config/detailed/PROJECT_NAME", headers={"X-Admin-Token": "test-admin-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "PROJECT_NAME"
    assert "value" in data
    assert "source" in data


@pytest.mark.asyncio
async def test_admin_config_detailed_redacted(async_client: AsyncClient):
    # DATABASE_URL contains sensitive info potentially, or just use a dummy
    # Actually, DATABASE_PASSWORD is a better bet for my patterns
    response = await async_client.get(
        "/admin/config/detailed/DATABASE_PASSWORD", headers={"X-Admin-Token": "test-admin-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "********"
