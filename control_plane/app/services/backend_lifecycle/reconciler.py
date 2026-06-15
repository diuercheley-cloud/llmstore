import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleContract,
    BackendObservedState,
    DriftRecord,
    LifecycleActionResult,
)

logger = logging.getLogger(__name__)


class DriftType:
    STATUS_MISMATCH = "status_mismatch"
    ACTIVE_MISMATCH = "active_mismatch"
    NOT_RUNNING = "not_running"
    UNEXPECTED_RUNNING = "unexpected_running"
    HEALTH_MISMATCH = "health_mismatch"


class BackendReconciler:
    def __init__(
        self,
        provider: BackendLifecycleContract,
        on_drift: Callable[[DriftRecord], None] | None = None,
    ):
        self._provider = provider
        self._on_drift = on_drift

    async def reconcile(
        self, desired: BackendDesiredState
    ) -> tuple[BackendObservedState, list[DriftRecord], LifecycleActionResult | None]:
        drifts: list[DriftRecord] = []
        action_result: LifecycleActionResult | None = None

        observed = await self._provider.get_observed_state(desired.backend_id, desired)
        drifts.extend(self._detect_drifts(desired, observed))

        if drifts and desired.is_active and not observed.running:
            action_result = await self._provider.start_backend(desired.backend_id, desired)
            if action_result.success:
                observed = await self._provider.get_observed_state(desired.backend_id, desired)
                drifts = self._detect_drifts(desired, observed)
            else:
                drifts.append(
                    DriftRecord(
                        backend_id=desired.backend_id,
                        backend_name=desired.name,
                        drift_type=DriftType.NOT_RUNNING,
                        desired="running",
                        observed=f"start failed: {action_result.error or action_result.message}",
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )
        elif drifts and not desired.is_active and observed.running:
            action_result = await self._provider.stop_backend(desired.backend_id, desired)
            if action_result.success:
                observed = await self._provider.get_observed_state(desired.backend_id, desired)
                drifts = self._detect_drifts(desired, observed)
            else:
                drifts.append(
                    DriftRecord(
                        backend_id=desired.backend_id,
                        backend_name=desired.name,
                        drift_type=DriftType.UNEXPECTED_RUNNING,
                        desired="stopped",
                        observed=f"stop failed: {action_result.error or action_result.message}",
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )

        for d in drifts:
            if self._on_drift:
                self._on_drift(d)

        return observed, drifts, action_result

    def _detect_drifts(
        self, desired: BackendDesiredState, observed: BackendObservedState
    ) -> list[DriftRecord]:
        drifts: list[DriftRecord] = []
        now = datetime.now(UTC).isoformat()

        if desired.is_active and not observed.running:
            drifts.append(
                DriftRecord(
                    backend_id=desired.backend_id,
                    backend_name=desired.name,
                    drift_type=DriftType.NOT_RUNNING,
                    desired="running",
                    observed=f"not running ({observed.error or 'unknown'})",
                    timestamp=now,
                )
            )
        elif not desired.is_active and observed.running:
            drifts.append(
                DriftRecord(
                    backend_id=desired.backend_id,
                    backend_name=desired.name,
                    drift_type=DriftType.UNEXPECTED_RUNNING,
                    desired="stopped",
                    observed="running",
                    timestamp=now,
                )
            )

        if observed.running and not observed.healthy:
            drifts.append(
                DriftRecord(
                    backend_id=desired.backend_id,
                    backend_name=desired.name,
                    drift_type=DriftType.HEALTH_MISMATCH,
                    desired="healthy",
                    observed=f"unhealthy ({observed.error or 'unknown'})",
                    timestamp=now,
                )
            )

        return drifts
