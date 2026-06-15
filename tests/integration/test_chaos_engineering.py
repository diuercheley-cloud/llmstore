import pytest
from app.core.config import get_settings
from app.services.chaos.injection import ChaosInjectionRegistry, inject_chaos


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_chaos_injection_latency():
    settings = get_settings()
    # Force enable chaos for test
    original_enabled = settings.chaos_enabled
    settings.chaos_enabled = True

    registry = ChaosInjectionRegistry.get_instance()
    registry.clear_injections()
    registry.add_injection("data_plane_latency", {"latency_ms": 100, "ratio": 1.0})

    import time

    start = time.perf_counter()
    await inject_chaos("data_plane_latency")
    duration = time.perf_counter() - start

    assert duration >= 0.1

    registry.clear_injections()
    settings.chaos_enabled = original_enabled


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_chaos_injection_redis_failure():
    settings = get_settings()
    original_enabled = settings.chaos_enabled
    settings.chaos_enabled = True

    registry = ChaosInjectionRegistry.get_instance()
    registry.clear_injections()
    registry.add_injection("redis_failure", {"ratio": 1.0})

    with pytest.raises(ConnectionError, match="Simulated chaos Redis"):
        await inject_chaos("redis_failure")

    registry.clear_injections()
    settings.chaos_enabled = original_enabled


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_chaos_injection_db_outage():
    settings = get_settings()
    original_enabled = settings.chaos_enabled
    settings.chaos_enabled = True

    registry = ChaosInjectionRegistry.get_instance()
    registry.clear_injections()
    registry.add_injection("db_outage", {"ratio": 1.0})

    with pytest.raises(RuntimeError, match="Simulated chaos Database"):
        await inject_chaos("db_outage")

    registry.clear_injections()
    settings.chaos_enabled = original_enabled
