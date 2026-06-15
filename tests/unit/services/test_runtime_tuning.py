import os

import pytest
from app.services.runtime_tuning import RuntimeTuningService


@pytest.mark.asyncio
async def test_recommendation_engine_queue_wait(db_session):
    service = RuntimeTuningService(db_session)
    # Mocking a benchmark with high queue wait
    from app.models.operations.runtime_tuning import RuntimeBenchmarkRun

    benchmark = RuntimeBenchmarkRun(
        model_id="test",
        tokens_per_sec=50,
        latency_p50=200,
        latency_p95=500,
        latency_p99=1000,
        queue_wait_ms=600,  # > 500
        gpu_memory_pressure=0.5,
        cpu_usage=50,
        cache_hit_ratio=0.1,
        fallback_rate=0,
        cost_per_1k_tokens=0.01,
        error_rate=0,
    )
    db_session.add(benchmark)
    await db_session.commit()

    await service.generate_recommendations(benchmark)

    recs = await service.get_recommendations()
    assert len(recs) > 0
    assert any(r.title == "Aumentar Paralelismo" for r in recs)


@pytest.mark.asyncio
async def test_apply_profile_advisory_by_default(db_session):
    service = RuntimeTuningService(db_session)
    await service.seed_default_profiles()

    # Ensure env var is not set
    if "RUNTIME_TUNING_APPLY_ENABLED" in os.environ:
        del os.environ["RUNTIME_TUNING_APPLY_ENABLED"]

    result = await service.apply_profile("low_latency")
    assert result["status"] == "success"
    assert result["advisory"] == True


@pytest.mark.asyncio
async def test_apply_profile_enforcement(db_session):
    service = RuntimeTuningService(db_session)
    await service.seed_default_profiles()

    os.environ["RUNTIME_TUNING_APPLY_ENABLED"] = "true"

    result = await service.apply_profile("high_throughput")
    assert result["status"] == "success"
    assert result["advisory"] == False

    # Check active profile
    active = await service.get_current_profile()
    assert active.name == "high_throughput"
