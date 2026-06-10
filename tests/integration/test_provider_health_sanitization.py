import pytest
from app.services.providers.registry import get_all_provider_health, get_provider, reload_registry


@pytest.fixture(autouse=True)
def reset_registry():
    reload_registry()
    yield
    reload_registry()


@pytest.mark.asyncio
async def test_local_health_check():
    local = get_provider("local")
    h = await local.health_check()
    assert h["provider_id"] == "local"
    assert h["healthy"] is True
    assert h["error"] is None


@pytest.mark.asyncio
async def test_cloud_health_no_api_key_does_not_crash():
    for pid in ("openai", "anthropic", "deepseek"):
        p = get_provider(pid)
        assert p is not None
        # Health check should not crash even without API key
        h = await p.health_check()
        assert h["provider_id"] == pid


@pytest.mark.asyncio
async def test_all_provider_health_sanitization():
    health_list = await get_all_provider_health()
    for h in health_list:
        assert h.provider_id is not None
        # No API keys or secrets should be in output
        if h.last_error_sanitized:
            assert "sk-" not in h.last_error_sanitized
            assert "api_key" not in h.last_error_sanitized.lower()


@pytest.mark.asyncio
async def test_openai_health_disabled():
    p = get_provider("openai")
    h = await p.health_check()
    if not p.enabled:
        assert h["healthy"] is None, "Disabled provider should have healthy=None"


@pytest.mark.asyncio
async def test_provider_list_models_no_side_effects():
    for pid in ("openai", "anthropic", "deepseek"):
        p = get_provider(pid)
        models = await p.list_models()
        assert isinstance(models, list)
        # Without API keys, should return empty list, not crash


@pytest.mark.asyncio
async def test_local_list_models():
    local = get_provider("local")
    models = await local.list_models()
    assert isinstance(models, list)
    assert len(models) > 0
