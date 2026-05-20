import os
import pytest
import pytest_asyncio
import yaml
from httpx import AsyncClient

from app.db.base import Base
from app.db.session import engine
import app.models.admin_rbac

from app.services.feature_flag_registry import FeatureFlagRegistryService

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

def test_feature_flags_service_basics():
    service = FeatureFlagRegistryService()
    flags = service.get_all_flags()
    assert len(flags) > 0
    
    # Check specific flag exist
    flag_names = {f["name"].upper() for f in flags}
    assert "ABUSE_DETECTION_ENABLED" in flag_names

    # Check details
    details = service.get_flag_by_name("ABUSE_DETECTION_ENABLED")
    assert details is not None
    assert details["name"] == "ABUSE_DETECTION_ENABLED"
    assert details["default"] is True

    # Check non-existent
    assert service.get_flag_by_name("NON_EXISTENT_FLAG_12345") is None

    # Check registry policy compliance
    valid, errors = service.validate_registry()
    assert valid is True
    assert len(errors) == 0

def test_feature_flags_validation_errors(tmp_path):
    mock_yaml = tmp_path / "mock-flags.yaml"
    mock_data = [
        {
            # Violation 1: High-risk default true
            "name": "HIGH_RISK_FLAG",
            "default": True,
            "owner": "platform-ops",
            "area": "core",
            "status": "active",
            "introduced_in": "v1.9.0",
            "risk_level": "high",
            "dependencies": [],
            "conflicts": [],
            "safe_default_reason": "Testing high risk defaults"
        },
        {
            # Violation 2: Experimental default true
            "name": "EXPERIMENTAL_FLAG",
            "default": True,
            "owner": "platform-ops",
            "area": "core",
            "status": "experimental",
            "introduced_in": "v1.9.0",
            "risk_level": "low",
            "dependencies": [],
            "conflicts": [],
            "safe_default_reason": "Testing experimental default"
        },
        {
            # Violation 3: Deprecated with no replacement/remove_after
            "name": "DEPRECATED_FLAG",
            "default": False,
            "owner": "platform-ops",
            "area": "core",
            "status": "deprecated",
            "introduced_in": "v1.9.0",
            "risk_level": "low",
            "dependencies": [],
            "conflicts": [],
            "safe_default_reason": "Testing deprecation rule"
        },
        {
            # Violation 4 & 5: Unregistered dependency/conflict
            "name": "DEP_CONFLICT_FLAG",
            "default": False,
            "owner": "platform-ops",
            "area": "core",
            "status": "active",
            "introduced_in": "v1.9.0",
            "risk_level": "low",
            "dependencies": ["UNREGISTERED_DEPENDENCY"],
            "conflicts": ["UNREGISTERED_CONFLICT"],
            "safe_default_reason": "Testing dependencies"
        }
    ]
    
    with open(mock_yaml, "w") as f:
        yaml.dump(mock_data, f)
        
    service = FeatureFlagRegistryService(registry_path=str(mock_yaml))
    valid, errors = service.validate_registry()
    
    assert valid is False
    assert len(errors) == 5
    
    err_str = " ".join(errors).lower()
    assert "high_risk_flag" in err_str and "high-risk" in err_str
    assert "experimental_flag" in err_str and "experimental" in err_str
    assert "deprecated_flag" in err_str and "deprecated" in err_str
    assert "unregistered_dependency" in err_str
    assert "unregistered_conflict" in err_str

@pytest.mark.asyncio
async def test_api_list_feature_flags(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

@pytest.mark.asyncio
async def test_api_get_flag_details(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags/ABUSE_DETECTION_ENABLED",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ABUSE_DETECTION_ENABLED"
    assert data["default"] is True

@pytest.mark.asyncio
async def test_api_get_flag_not_found(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags/NON_EXISTENT_FLAG_123",
        headers=admin_token_headers
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_api_get_deprecated_flags(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags/deprecated",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_api_get_conflicts(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags/conflicts",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_api_validate_registry(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/feature-flags/deprecated",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    
    response = await async_client.post(
        "/admin/feature-flags/validate",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "valid"
