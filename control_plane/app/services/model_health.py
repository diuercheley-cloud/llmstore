# Owner: agent-platform
import logging
import uuid
from datetime import UTC
from typing import Any

from app.core.time import utc_now
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_health import ModelHealthStatus
from app.models.core.model_registry import ModelRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class ModelHealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_health_check(
        self,
        backend_id: uuid.UUID,
        model_id: str,
        route_id: uuid.UUID | None = None,
        success: bool = True,
        latency_ms: float = 0.0,
        error_rate: float = 0.0,
        circuit_breaker_state: str = "closed",
    ) -> ModelHealthStatus:
        """
        Record or update health check status for a backend route.
        """
        stmt = select(ModelHealthStatus).where(
            ModelHealthStatus.backend_id == backend_id, ModelHealthStatus.model_id == model_id
        )
        if route_id:
            stmt = stmt.where(ModelHealthStatus.route_id == route_id)

        res = await self.db.execute(stmt)
        status = res.scalar_one_or_none()

        now = utc_now()
        if not status:
            status = ModelHealthStatus(
                backend_id=backend_id,
                model_id=model_id,
                route_id=route_id,
                circuit_breaker_state=circuit_breaker_state,
                latency_p95=latency_ms,
                error_rate=error_rate,
                last_success_at=now if success else None,
                last_failure_at=now if not success else None,
                updated_at=now,
            )
            self.db.add(status)
        else:
            status.circuit_breaker_state = circuit_breaker_state
            status.latency_p95 = latency_ms
            status.error_rate = error_rate
            if success:
                status.last_success_at = now
            else:
                status.last_failure_at = now
            status.updated_at = now
            self.db.add(status)

        await self.db.commit()
        return status

    async def get_model_health_summary(
        self, heart_beat_window_seconds: int = 300
    ) -> dict[str, Any]:
        """
        Calculates and returns:
          - online_models_count
          - degraded_models_count
          - offline_models_count
          - source: "health_state"
        """
        # Fetch all models
        stmt_models = select(ModelRegistry).options(
            selectinload(ModelRegistry.backend_routes).selectinload(
                ModelBackendRoute.inference_backend
            )
        )
        res_models = await self.db.execute(stmt_models)
        models = res_models.scalars().all()

        # Fetch all health statuses
        res_health = await self.db.execute(select(ModelHealthStatus))
        health_statuses = res_health.scalars().all()

        # Group health statuses by (backend_id, model_id)
        health_map = {}
        for h in health_statuses:
            health_map[(h.backend_id, h.model_id)] = h

        online_count = 0
        degraded_count = 0
        offline_count = 0

        now = utc_now()

        for model in models:
            routes = model.backend_routes
            if not routes:
                offline_count += 1
                continue

            route_states = []
            for route in routes:
                backend = route.inference_backend
                # Check if backend is active/healthy (based on backend is_active flag)
                if not backend or not backend.is_active:
                    route_states.append("offline")
                    continue

                health = health_map.get((backend.id, model.model_id))
                if not health:
                    route_states.append("offline")
                    continue

                # 1. Lack of heartbeat check
                if not health.last_success_at:
                    route_states.append("offline")
                    continue

                last_success = health.last_success_at
                if last_success.tzinfo is None:
                    last_success = last_success.replace(tzinfo=UTC)

                time_since_success = (now - last_success).total_seconds()
                if time_since_success > heart_beat_window_seconds:
                    route_states.append("offline")
                    continue

                # 2. Degraded check
                is_degraded = (
                    health.circuit_breaker_state in ("open", "half-open")
                    or health.error_rate > 0.1
                    or health.latency_p95 > 2000.0
                )

                if is_degraded:
                    route_states.append("degraded")
                else:
                    route_states.append("online")

            # Aggregate state for this model
            if "online" in route_states:
                online_count += 1
            elif "degraded" in route_states:
                degraded_count += 1
            else:
                offline_count += 1

        return {
            "online_models_count": online_count,
            "degraded_models_count": degraded_count,
            "offline_models_count": offline_count,
            "source": "health_state",
        }
