import os

# Import models to register on Base.metadata
import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import engine
from app.services.runtime_profiles import RuntimeProfilesService
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

def test_runtime_profiles_service_basics():
    service = RuntimeProfilesService()
    profiles = service.get_all_profiles()
    assert len(profiles) == 5
    
    # Check specific profiles exist
    ids = [p["profile_id"] for p in profiles]
    assert "appliance-small" in ids
    assert "enterprise-edge" in ids
    assert "sovereign-cluster" in ids
    assert "managed-hybrid" in ids
    assert "compliance-mode" in ids

    # Check validation
    valid, errors = service.validate_profile("appliance-small")
    assert valid is True
    assert len(errors) == 0

    # Check validation fails for non-existent profile
    valid, errors = service.validate_profile("non-existent")
    assert valid is False
    assert len(errors) > 0

@pytest.mark.asyncio
async def test_api_list_profiles(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/runtime-profiles",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5

@pytest.mark.asyncio
async def test_api_get_current_settings(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.get(
        "/admin/runtime-profiles/current",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "DEPLOYMENT_MODE" in data or "PROJECT_NAME" in data

@pytest.mark.asyncio
async def test_api_validate_profile(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.post(
        "/admin/runtime-profiles/validate",
        json={"profile_id": "appliance-small"},
        headers=admin_token_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "valid"

    # Test invalid profile validation
    response = await async_client.post(
        "/admin/runtime-profiles/validate",
        json={"profile_id": "non-existent"},
        headers=admin_token_headers
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_api_apply_profile_dry_run(async_client: AsyncClient, admin_token_headers: dict):
    response = await async_client.post(
        "/admin/runtime-profiles/apply",
        json={"profile_id": "appliance-small", "dry_run": True},
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["dry_run"] is True
    assert "diff" in data

@pytest.mark.asyncio
async def test_api_apply_profile_live_disabled_by_default(async_client: AsyncClient, admin_token_headers: dict):
    # Ensure apply enabled env var is cleared/disabled
    old_env = os.environ.get("RUNTIME_PROFILE_APPLY_ENABLED")
    if "RUNTIME_PROFILE_APPLY_ENABLED" in os.environ:
        del os.environ["RUNTIME_PROFILE_APPLY_ENABLED"]

    try:
        response = await async_client.post(
            "/admin/runtime-profiles/apply",
            json={"profile_id": "appliance-small", "dry_run": False},
            headers=admin_token_headers
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()
    finally:
        if old_env is not None:
            os.environ["RUNTIME_PROFILE_APPLY_ENABLED"] = old_env

@pytest.mark.asyncio
async def test_api_apply_profile_live_enabled(async_client: AsyncClient, admin_token_headers: dict):
    os.environ["RUNTIME_PROFILE_APPLY_ENABLED"] = "true"
    service = RuntimeProfilesService()
    
    # Ensure a clean slate for the test mock env file
    if os.path.exists(service.env_path):
        os.remove(service.env_path)
    if os.path.exists(service.backup_path):
        os.remove(service.backup_path)

    with open(service.env_path, "w", encoding="utf-8") as f:
        f.write("DEPLOYMENT_MODE=hybrid\nMAX_QUEUE_SIZE=8\n")

    try:
        response = await async_client.post(
            "/admin/runtime-profiles/apply",
            json={"profile_id": "appliance-small", "dry_run": False},
            headers=admin_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["dry_run"] is False
        
        # Verify the backup file was created
        assert os.path.exists(service.backup_path)
        
        # Verify rollback API works
        response_rollback = await async_client.post(
            "/admin/runtime-profiles/apply",
            json={"rollback": True, "dry_run": False},
            headers=admin_token_headers
        )
        assert response_rollback.status_code == 200
        data_rb = response_rollback.json()
        assert data_rb["status"] == "success"
        assert data_rb["dry_run"] is False

    finally:
        if "RUNTIME_PROFILE_APPLY_ENABLED" in os.environ:
            del os.environ["RUNTIME_PROFILE_APPLY_ENABLED"]
