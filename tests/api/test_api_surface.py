import os

import pytest
import pytest_asyncio
import yaml
from app.db.base import Base
from app.db.session import engine
from httpx import AsyncClient

from scripts.check_api_surface import check_surface


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_api_surface_deprecated_endpoint(async_client: AsyncClient, admin_token_headers: dict):
    # GET /admin/models/runtime is marked as deprecated
    response = await async_client.get("/admin/models/runtime", headers=admin_token_headers)
    assert response.status_code == 200
    
    assert response.headers.get("X-API-Surface-Status") == "deprecated"
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
    assert response.headers.get("X-Replacement-Endpoint") == "/admin/models/lifecycle"


@pytest.mark.asyncio
async def test_api_surface_supported_endpoint(async_client: AsyncClient, admin_token_headers: dict):
    # GET /admin/system/api-surface is marked as supported
    response = await async_client.get("/admin/system/api-surface", headers=admin_token_headers)
    assert response.status_code == 200
    
    assert response.headers.get("X-API-Surface-Status") == "supported"
    assert "X-Deprecated-Endpoint" not in response.headers
    assert "X-Replacement-Endpoint" not in response.headers


@pytest.mark.asyncio
async def test_api_surface_get_system_api_surface_data(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get("/admin/system/api-surface", headers=admin_token_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check that a known entry exists
    found_deprecated = False
    for entry in data:
        if entry["endpoint"] == "/admin/models/runtime" and entry["method"] == "GET":
            assert entry["status"] == "deprecated"
            assert entry["replacement"] == "/admin/models/lifecycle"
            found_deprecated = True
            break
            
    assert found_deprecated is True


def test_api_surface_check_fails_on_unclassified(monkeypatch, tmp_path):
    # Mock yaml_path in scripts/legacy/check_api_surface.py to a file missing endpoints
    mock_yaml = tmp_path / "mock-api-surface.yaml"
    # Write only one endpoint in it
    mock_data = [
        {
            "endpoint": "/",
            "method": "GET",
            "owner": "platform-ops",
            "status": "supported",
            "replacement": None,
            "since_version": "1.0.0",
            "deprecation_version": None,
            "docs_url": "/docs/api/supported-api-surface.md"
        }
    ]
    with open(mock_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(mock_data, f)
        
    # Monkeypatch the base_dir or yaml_path in scripts/check_api_surface
    monkeypatch.setattr("scripts.check_api_surface.base_dir", str(tmp_path))
    # Rename mock file to expected location
    os.makedirs(tmp_path / "config", exist_ok=True)
    os.rename(mock_yaml, tmp_path / "config/api-surface.yaml")

    # Run check_surface and expect SystemExit with code 1
    with pytest.raises(SystemExit) as exc_info:
        check_surface()
    assert exc_info.value.code == 1
