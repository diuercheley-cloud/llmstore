from datetime import timedelta

import pytest
from app.core.time import utc_now
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.services.model_health import ModelHealthService
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_admin_usage_summary_real_health_state(
    isolated_db_url: str,
    admin_client: AsyncClient,
    admin_token_headers: dict[str, str],
):
    # Setup test data in the shared in-memory database
    engine = create_async_engine(isolated_db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        # Create models
        m_online = ModelRegistry(model_id="model-online", model_file="models/m1.bin")
        m_degraded = ModelRegistry(model_id="model-degraded", model_file="models/m2.bin")
        m_offline_hb = ModelRegistry(model_id="model-offline-hb", model_file="models/m3.bin")
        m_offline_inactive = ModelRegistry(
            model_id="model-offline-inactive", model_file="models/m4.bin"
        )

        session.add_all([m_online, m_degraded, m_offline_hb, m_offline_inactive])
        await session.commit()

        # Create backends
        b_online = InferenceBackend(
            name="b-online", provider="local", backend_url="http://localhost/b1", is_active=True
        )
        b_degraded = InferenceBackend(
            name="b-degraded", provider="local", backend_url="http://localhost/b2", is_active=True
        )
        b_offline = InferenceBackend(
            name="b-offline", provider="local", backend_url="http://localhost/b3", is_active=True
        )
        b_inactive = InferenceBackend(
            name="b-inactive", provider="local", backend_url="http://localhost/b4", is_active=False
        )

        session.add_all([b_online, b_degraded, b_offline, b_inactive])
        await session.commit()

        # Create routes
        r_online = ModelBackendRoute(
            model_registry_id=m_online.id, inference_backend_id=b_online.id
        )
        r_degraded = ModelBackendRoute(
            model_registry_id=m_degraded.id, inference_backend_id=b_degraded.id
        )
        r_offline_hb = ModelBackendRoute(
            model_registry_id=m_offline_hb.id, inference_backend_id=b_offline.id
        )
        r_offline_inactive = ModelBackendRoute(
            model_registry_id=m_offline_inactive.id, inference_backend_id=b_inactive.id
        )

        session.add_all([r_online, r_degraded, r_offline_hb, r_offline_inactive])
        await session.commit()

        # Record health check statuses
        health_service = ModelHealthService(session)

        # 1. Online: recent success
        await health_service.record_health_check(
            backend_id=b_online.id,
            model_id=m_online.model_id,
            route_id=r_online.id,
            success=True,
            latency_ms=100.0,
            error_rate=0.0,
            circuit_breaker_state="closed",
        )

        # 2. Degraded: open breaker
        await health_service.record_health_check(
            backend_id=b_degraded.id,
            model_id=m_degraded.model_id,
            route_id=r_degraded.id,
            success=True,
            circuit_breaker_state="open",
        )

        # 3. Offline (no heartbeat): old check (e.g. 10 minutes ago)
        status = await health_service.record_health_check(
            backend_id=b_offline.id,
            model_id=m_offline_hb.model_id,
            route_id=r_offline_hb.id,
            success=True,
        )
        status.last_success_at = utc_now() - timedelta(minutes=10)
        session.add(status)
        await session.commit()

        # 4. Offline (inactive backend): recent check but backend.is_active=False
        await health_service.record_health_check(
            backend_id=b_inactive.id,
            model_id=m_offline_inactive.model_id,
            route_id=r_offline_inactive.id,
            success=True,
        )

    await engine.dispose()

    # Call usage summary API
    response = await admin_client.get(
        "/admin/usage/summary",
        headers=admin_token_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "totals" in data

    totals = data["totals"]
    assert totals["online_models_count"] == 1
    assert totals["degraded_models_count"] == 1
    assert totals["offline_models_count"] == 2
    assert totals["source"] == "health_state"

    # Compatibility assertions
    assert totals["models_online"] == 1
    assert totals["models_total"] == 4
