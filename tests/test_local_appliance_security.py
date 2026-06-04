import pytest
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_status_shows_appliance_mode(admin_client):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    settings.local_appliance_mode = True
    
    try:
        response = await admin_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "appliance_mode" in data
        assert data["appliance_mode"] is True
    finally:
        settings.local_appliance_mode = original_mode

@pytest.mark.asyncio
async def test_deep_health_shows_appliance_mode_and_warnings(admin_client):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    original_token = settings.admin_token
    
    settings.local_appliance_mode = True
    settings.admin_token = "default-admin-token"
    headers = {"X-Admin-Token": "default-admin-token"}
    
    try:
        response = await admin_client.get("/admin/health/deep", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["api"]["appliance_mode"] is True
        assert any("Insecure default ADMIN_TOKEN" in w for w in data["warnings"])
    finally:
        settings.local_appliance_mode = original_mode
        settings.admin_token = original_token
