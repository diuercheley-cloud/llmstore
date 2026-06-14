import pytest
import uuid
from datetime import datetime, timezone, timedelta

from app.core.time import utc_now
from app.models.core.model_registry import ModelRegistry
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_health import ModelHealthStatus
from app.services.model_health import ModelHealthService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_model_online_recent_health_check(db_session: AsyncSession):
    # 1. Create model
    model = ModelRegistry(
        model_id="test-model-online",
        model_file="models/test-model-online.bin",
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()

    # 2. Create active backend
    backend = InferenceBackend(
        name="backend-online",
        provider="local",
        backend_url="http://localhost:8081",
        is_active=True,
    )
    db_session.add(backend)
    await db_session.commit()

    # 3. Create route
    route = ModelBackendRoute(
        model_registry_id=model.id,
        inference_backend_id=backend.id,
        priority=100,
        weight=100,
        state="healthy",
    )
    db_session.add(route)
    await db_session.commit()

    # 4. Record successful health check
    service = ModelHealthService(db_session)
    await service.record_health_check(
        backend_id=backend.id,
        model_id=model.model_id,
        route_id=route.id,
        success=True,
        latency_ms=150.0,
        error_rate=0.01,
        circuit_breaker_state="closed",
    )

    # 5. Verify health summary
    summary = await service.get_model_health_summary(heart_beat_window_seconds=300)
    assert summary["online_models_count"] == 1
    assert summary["degraded_models_count"] == 0
    assert summary["offline_models_count"] == 0
    assert summary["source"] == "health_state"


@pytest.mark.asyncio
async def test_model_degraded_by_metrics(db_session: AsyncSession):
    service = ModelHealthService(db_session)

    # Helper function to setup model, backend, route
    async def setup_route(model_id: str, backend_name: str):
        model = ModelRegistry(
            model_id=model_id,
            model_file=f"models/{model_id}.bin",
            is_active=True,
        )
        backend = InferenceBackend(
            name=backend_name,
            provider="local",
            backend_url=f"http://localhost/{backend_name}",
            is_active=True,
        )
        db_session.add_all([model, backend])
        await db_session.commit()

        route = ModelBackendRoute(
            model_registry_id=model.id,
            inference_backend_id=backend.id,
        )
        db_session.add(route)
        await db_session.commit()
        return model, backend, route

    # Case A: degraded by circuit breaker open
    model_a, backend_a, route_a = await setup_route("model-a", "backend-a")
    await service.record_health_check(
        backend_id=backend_a.id,
        model_id=model_a.model_id,
        route_id=route_a.id,
        success=True,
        circuit_breaker_state="open",
    )

    # Case B: degraded by high error rate
    model_b, backend_b, route_b = await setup_route("model-b", "backend-b")
    await service.record_health_check(
        backend_id=backend_b.id,
        model_id=model_b.model_id,
        route_id=route_b.id,
        success=True,
        error_rate=0.2,
    )

    # Case C: degraded by high latency
    model_c, backend_c, route_c = await setup_route("model-c", "backend-c")
    await service.record_health_check(
        backend_id=backend_c.id,
        model_id=model_c.model_id,
        route_id=route_c.id,
        success=True,
        latency_ms=2500.0,
    )

    summary = await service.get_model_health_summary(heart_beat_window_seconds=300)
    assert summary["degraded_models_count"] == 3
    assert summary["online_models_count"] == 0
    assert summary["offline_models_count"] == 0


@pytest.mark.asyncio
async def test_model_offline_missing_heartbeat(db_session: AsyncSession):
    # Setup model, backend, route
    model = ModelRegistry(
        model_id="model-offline-heartbeat",
        model_file="models/model-offline-heartbeat.bin",
        is_active=True,
    )
    backend = InferenceBackend(
        name="backend-offline-heartbeat",
        provider="local",
        backend_url="http://localhost/offline",
        is_active=True,
    )
    db_session.add_all([model, backend])
    await db_session.commit()

    route = ModelBackendRoute(
        model_registry_id=model.id,
        inference_backend_id=backend.id,
    )
    db_session.add(route)
    await db_session.commit()

    # Record check but make it old
    service = ModelHealthService(db_session)
    status = await service.record_health_check(
        backend_id=backend.id,
        model_id=model.model_id,
        route_id=route.id,
        success=True,
    )

    # Artificially set last_success_at to 10 minutes ago
    status.last_success_at = utc_now() - timedelta(minutes=10)
    db_session.add(status)
    await db_session.commit()

    # Check summary (window = 5 minutes / 300s)
    summary = await service.get_model_health_summary(heart_beat_window_seconds=300)
    assert summary["offline_models_count"] == 1
    assert summary["online_models_count"] == 0
    assert summary["degraded_models_count"] == 0


@pytest.mark.asyncio
async def test_model_offline_inactive_backend(db_session: AsyncSession):
    # Setup model, but inactive backend
    model = ModelRegistry(
        model_id="model-inactive-backend",
        model_file="models/model-inactive-backend.bin",
        is_active=True,
    )
    backend = InferenceBackend(
        name="backend-inactive",
        provider="local",
        backend_url="http://localhost/inactive",
        is_active=False,  # INACTIVE backend
    )
    db_session.add_all([model, backend])
    await db_session.commit()

    route = ModelBackendRoute(
        model_registry_id=model.id,
        inference_backend_id=backend.id,
    )
    db_session.add(route)
    await db_session.commit()

    service = ModelHealthService(db_session)
    await service.record_health_check(
        backend_id=backend.id,
        model_id=model.model_id,
        route_id=route.id,
        success=True,
    )

    # The backend is inactive, so the model should be considered offline, not online or degraded
    summary = await service.get_model_health_summary(heart_beat_window_seconds=300)
    assert summary["offline_models_count"] == 1
    assert summary["online_models_count"] == 0
    assert summary["degraded_models_count"] == 0
