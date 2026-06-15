import pytest
from app.services.supported_surface import SupportedSurfaceService
from httpx import AsyncClient


def test_supported_surface_service():
    service = SupportedSurfaceService()
    caps = service.get_all_capabilities()
    assert len(caps) >= 19

    # Test get by ID
    openai_cap = service.get_capability_by_id("openai-api")
    assert openai_cap is not None
    assert openai_cap["name"] == "OpenAI-compatible API"
    assert openai_cap["status"] == "keep_supported"
    assert "limitations" in openai_cap

    # Test get by ID not found
    none_cap = service.get_capability_by_id("non-existent")
    assert none_cap is None

    # Test get by status
    advisory_caps = service.get_capabilities_by_status("advisory")
    assert len(advisory_caps) >= 3
    for cap in advisory_caps:
        assert cap["status"] == "advisory"


@pytest.mark.asyncio
async def test_get_all_surfaces(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/support/surface", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 19

    # Assert fields are present
    first_item = data[0]
    required_fields = {
        "id",
        "name",
        "area",
        "status",
        "owner",
        "support_level",
        "docs_url",
        "since_version",
        "limitations",
        "test_coverage",
    }
    for field in required_fields:
        assert field in first_item


@pytest.mark.asyncio
async def test_get_surface_by_id(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/support/surface/openai-api", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "openai-api"
    assert data["name"] == "OpenAI-compatible API"
    assert data["status"] == "keep_supported"


@pytest.mark.asyncio
async def test_get_surface_by_id_not_found(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/support/surface/invalid-cap-id", headers=admin_token_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_surfaces_by_status(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/support/surface/status/keep_supported", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert item["status"] == "keep_supported"


@pytest.mark.asyncio
async def test_get_surfaces_by_invalid_status(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/support/surface/status/invalidstatus", headers=admin_token_headers
    )
    assert response.status_code == 400
    assert "invalid status" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    response = await async_client.get("/admin/support/surface")
    assert response.status_code == 401
