from app.core.config import Settings


def test_cors_defaults_appliance_mode_empty_origins():
    # Empty CORS_ALLOW_ORIGINS in appliance mode should use secure defaults
    settings = Settings(
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8000",
        LOCAL_APPLIANCE_MODE=True,
        CORS_ALLOW_ORIGINS="",
        PUBLIC_BASE_URL="http://localhost:18080"
    )
    
    origins = settings.cors_origins
    assert "http://localhost" in origins
    assert "http://127.0.0.1" in origins
    assert "http://localhost:18080" in origins
    assert "*" not in origins
    
    warnings = settings.cors_warnings
    assert any(w["id"] == "CORS_EMPTY_APPLIANCE" for w in warnings)

def test_cors_forbid_wildcard_in_appliance_mode():
    settings = Settings(
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8000",
        LOCAL_APPLIANCE_MODE=True,
        CORS_ALLOW_ORIGINS="*",
        PUBLIC_BASE_URL="http://localhost:18080"
    )
    
    origins = settings.cors_origins
    assert "*" not in origins
    # Should still have defaults
    assert "http://localhost:18080" in origins
    
    warnings = settings.cors_warnings
    assert any(w["id"] == "CORS_WILDCARD_APPLIANCE" for w in warnings)

def test_cors_allow_custom_origins_in_appliance_mode():
    settings = Settings(
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8000",
        LOCAL_APPLIANCE_MODE=True,
        CORS_ALLOW_ORIGINS="http://my-app.local,https://secure.internal",
        PUBLIC_BASE_URL="http://localhost:18080"
    )
    
    origins = settings.cors_origins
    assert "http://my-app.local" in origins
    assert "https://secure.internal" in origins
    assert "http://localhost:18080" in origins
    
    warnings = settings.cors_warnings
    # No warnings for custom valid origins
    assert not any(w["id"] == "CORS_EMPTY_APPLIANCE" for w in warnings)
    assert not any(w["id"] == "CORS_WILDCARD_APPLIANCE" for w in warnings)

def test_cors_invalid_origin_warning():
    settings = Settings(
        ADMIN_TOKEN="test-token",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8000",
        LOCAL_APPLIANCE_MODE=True,
        CORS_ALLOW_ORIGINS="not-a-url",
        PUBLIC_BASE_URL="http://localhost:18080"
    )
    
    origins = settings.cors_origins
    assert "not-a-url" not in origins
    
    warnings = settings.cors_warnings
    assert any(w["id"] == "CORS_INVALID_ORIGIN" for w in warnings)
