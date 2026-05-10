import pytest
from app.core.config import Settings

def test_appliance_mode_enforces_secure_defaults():
    # Test that setting LOCAL_APPLIANCE_MODE=True enforces other secure settings
    settings = Settings(
        LOCAL_APPLIANCE_MODE=True,
        LOCALHOST_MODE=False,  # Should be overridden
        LOCAL_BILLING_MODE="stripe",  # Should be overridden
        PUBLIC_EXPOSURE=True,  # Should be overridden
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8081"
    )
    
    assert settings.local_appliance_mode is True
    assert settings.localhost_mode is True
    assert settings.local_billing_mode == "manual"
    assert settings.public_exposure is False
    assert settings.public_signup_enabled is False

def test_appliance_mode_restricts_cors():
    settings = Settings(
        LOCAL_APPLIANCE_MODE=True,
        CORS_ALLOW_ORIGINS="*",  # Should be restricted
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8081"
    )
    
    origins = settings.cors_origins
    assert "*" not in origins
    assert "http://localhost" in origins
    assert "http://127.0.0.1" in origins

def test_appliance_mode_disabled_defaults():
    settings = Settings(
        LOCAL_APPLIANCE_MODE=False,
        LOCALHOST_MODE=False,
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8081"
    )
    
    assert settings.local_appliance_mode is False
    # Should respect explicit values when appliance mode is off
    assert settings.localhost_mode is False
