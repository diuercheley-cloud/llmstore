import pytest
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_status_endpoint_cors_configured(admin_client):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    settings.local_appliance_mode = True
    
    try:
        response = await admin_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "cors_configured" in data
        assert data["cors_configured"] is True
    finally:
        settings.local_appliance_mode = original_mode

@pytest.mark.asyncio
async def test_deep_health_cors_warnings(admin_client, admin_token_headers):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    original_cors = settings.cors_allow_origins
    
    settings.local_appliance_mode = True
    settings.cors_allow_origins = "*"
    
    try:
        response = await admin_client.get("/admin/health/deep", headers=admin_token_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check security info
        assert "security" in data
        assert data["security"]["cors_configured"] is True
        assert any(w["id"] == "CORS_WILDCARD_APPLIANCE" for w in data["security"]["cors_warnings"])
        
        # Check top-level warnings
        assert any("CORS: Wildcard '*' CORS is not allowed" in w for w in data["warnings"])
        # In test env, it might be NOT_READY due to migrations, so we just check it's not READY
        assert data["readiness_score"] != "READY"
    finally:
        settings.local_appliance_mode = original_mode
        settings.cors_allow_origins = original_cors
