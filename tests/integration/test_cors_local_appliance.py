import pytest
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_cors_preflight_localhost(admin_client):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    settings.local_appliance_mode = True

    try:
        # Test OPTIONS preflight
        headers = {
            "Origin": "http://localhost:18080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
        response = await admin_client.options("/health", headers=headers)

        # If it's 200/204, CORS middleware allowed it
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin") == "http://localhost:18080"
    finally:
        settings.local_appliance_mode = original_mode


@pytest.mark.asyncio
async def test_cors_forbidden_origin(admin_client):
    settings = get_settings()
    original_mode = settings.local_appliance_mode
    settings.local_appliance_mode = True

    try:
        headers = {
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        }
        response = await admin_client.options("/health", headers=headers)

        # CORS middleware returns 200/204 but WITHOUT the allow-origin header if denied
        assert (
            "access-control-allow-origin" not in response.headers
            or response.headers.get("access-control-allow-origin") != "http://evil.com"
        )
    finally:
        settings.local_appliance_mode = original_mode
