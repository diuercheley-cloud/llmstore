import logging
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendLifecycleContract,
    BackendObservedState,
    DriftRecord,
    LifecycleActionResult,
)
from app.models.core.inference_backend import InferenceBackend
from app.services.backend_lifecycle.providers.base import ProviderUnavailableError
from app.services.backend_lifecycle.reconciler import BackendReconciler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BackendLifecycleManager:
    def __init__(
        self,
        db: AsyncSession,
        provider: BackendLifecycleContract,
        audit_callback: Callable | None = None,
    ):
        self._db = db
        self._provider = provider
        self._reconciler = BackendReconciler(provider, on_drift=self._on_drift)
        self._audit_callback = audit_callback
        self._drift_history: list[DriftRecord] = []

    def provider(self) -> BackendLifecycleContract:
        return self._provider

    def capabilities(self) -> BackendLifecycleCapabilities:
        return self._provider.capabilities()

    def drift_history(self) -> list[DriftRecord]:
        return list(self._drift_history)

    async def get_desired_state(self, backend_id: UUID) -> BackendDesiredState | None:
        backend = await self._db.get(InferenceBackend, backend_id)
        if backend is None:
            return None
        return self._to_desired(backend)

    async def get_observed_state(self, backend_id: UUID) -> BackendObservedState:
        desired = await self.get_desired_state(backend_id)
        if desired is None:
            return BackendObservedState(
                backend_id=backend_id,
                provider="unknown",
                running=False,
                healthy=False,
                error="backend not found",
            )
        return await self._provider.get_observed_state(backend_id, desired)

    async def reconcile_one(self, backend_id: UUID) -> dict:
        desired = await self.get_desired_state(backend_id)
        if desired is None:
            return {"error": "backend not found", "backend_id": str(backend_id)}
        observed, drifts, action = await self._reconciler.reconcile(desired)
        result = {
            "backend_id": str(backend_id),
            "desired": desired.model_dump(),
            "observed": observed.model_dump(),
            "drifts": [d.model_dump() for d in drifts],
            "action": action.model_dump() if action else None,
        }
        await self._audit("reconcile", result)
        return result

    async def reconcile_all(self) -> list[dict]:
        rows = (await self._db.execute(select(InferenceBackend))).scalars().all()
        results = []
        for backend in rows:
            try:
                result = await self.reconcile_one(backend.id)
                results.append(result)
            except Exception as exc:
                logger.error("reconcile failed for %s: %s", backend.id, exc)
                results.append({"backend_id": str(backend.id), "error": str(exc)})
        return results

    async def start_backend(self, backend_id: UUID) -> LifecycleActionResult:
        desired = await self.get_desired_state(backend_id)
        if desired is None:
            return LifecycleActionResult(
                success=False,
                action="start",
                backend_id=backend_id,
                message="backend not found",
            )
        caps = self._provider.capabilities()
        if not caps.can_start:
            raise ProviderUnavailableError(caps.provider_type, "start not supported")
        result = await self._provider.start_backend(backend_id, desired)
        if result.success:
            await self._update_status(backend_id, "running", True)
        await self._audit("start", {"backend_id": str(backend_id), "result": result.model_dump()})
        return result

    async def stop_backend(self, backend_id: UUID) -> LifecycleActionResult:
        desired = await self.get_desired_state(backend_id)
        if desired is None:
            return LifecycleActionResult(
                success=False,
                action="stop",
                backend_id=backend_id,
                message="backend not found",
            )
        caps = self._provider.capabilities()
        if not caps.can_stop:
            raise ProviderUnavailableError(caps.provider_type, "stop not supported")
        result = await self._provider.stop_backend(backend_id, desired)
        if result.success:
            await self._update_status(backend_id, "stopped", False)
        await self._audit("stop", {"backend_id": str(backend_id), "result": result.model_dump()})
        return result

    async def restart_backend(self, backend_id: UUID) -> LifecycleActionResult:
        desired = await self.get_desired_state(backend_id)
        if desired is None:
            return LifecycleActionResult(
                success=False,
                action="restart",
                backend_id=backend_id,
                message="backend not found",
            )
        caps = self._provider.capabilities()
        if not caps.can_restart:
            raise ProviderUnavailableError(caps.provider_type, "restart not supported")
        result = await self._provider.restart_backend(backend_id, desired)
        if result.success:
            await self._update_status(backend_id, "running", True)
        await self._audit("restart", {"backend_id": str(backend_id), "result": result.model_dump()})
        return result

    async def _update_status(self, backend_id: UUID, status: str, is_active: bool) -> None:
        backend = await self._db.get(InferenceBackend, backend_id)
        if backend:
            backend.status = status
            backend.is_active = is_active
            backend.updated_at = datetime.now(UTC)
            await self._db.commit()

    def _on_drift(self, drift: DriftRecord) -> None:
        self._drift_history.append(drift)
        logger.warning(
            "drift detected: backend=%s type=%s desired=%s observed=%s",
            drift.backend_name,
            drift.drift_type,
            drift.desired,
            drift.observed,
        )

    async def _audit(self, action: str, details: dict) -> None:
        if self._audit_callback:
            try:
                if callable(self._audit_callback):
                    result = self._audit_callback(action, details)
                    if hasattr(result, "__await__"):
                        await result
            except Exception as exc:
                logger.error("audit callback failed: %s", exc)
        self._record_metric(action, details)

    def _record_metric(self, action: str, details: dict) -> None:
        try:
            from app.core.metrics import SECURITY_EVENT_COUNTER

            SECURITY_EVENT_COUNTER.labels(
                event_type=f"backend_lifecycle_{action}",
                severity="info",
            ).inc()
        except Exception:
            pass

    def _to_desired(self, backend: InferenceBackend) -> BackendDesiredState:
        return BackendDesiredState(
            backend_id=backend.id,
            name=backend.name,
            provider=backend.provider,
            backend_url=backend.backend_url,
            is_active=backend.is_active,
            status=backend.status,
            metadata_json=backend.metadata_json,
        )
