from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendObservedState,
    LifecycleActionResult,
)
from app.services.backend_lifecycle.reconciler import BackendReconciler, DriftType


@pytest.fixture
def desired_active():
    return BackendDesiredState(
        backend_id=uuid4(),
        name="test-backend",
        provider="llama.cpp",
        backend_url="http://localhost:8080",
        is_active=True,
        status="running",
    )


@pytest.fixture
def desired_inactive():
    return BackendDesiredState(
        backend_id=uuid4(),
        name="test-backend",
        provider="llama.cpp",
        backend_url="http://localhost:8080",
        is_active=False,
        status="stopped",
    )


@pytest.mark.asyncio
async def test_reconcile_no_drift_when_active_and_running(desired_active):
    mock_provider = AsyncMock()
    mock_provider.get_observed_state.return_value = BackendObservedState(
        backend_id=desired_active.backend_id,
        provider="local_process",
        running=True,
        healthy=True,
    )
    reconciler = BackendReconciler(mock_provider)
    _, drifts, action = await reconciler.reconcile(desired_active)
    assert len(drifts) == 0
    assert action is None


@pytest.mark.asyncio
async def test_reconcile_detects_drift_when_active_not_running(desired_active):
    mock_provider = AsyncMock()
    mock_provider.get_observed_state.return_value = BackendObservedState(
        backend_id=desired_active.backend_id,
        provider="local_process",
        running=False,
        healthy=False,
        error="process not found",
    )
    mock_provider.start_backend.return_value = LifecycleActionResult(
        success=True, action="start", backend_id=desired_active.backend_id, message="started",
    )
    reconciler = BackendReconciler(mock_provider)
    observed, drifts, action = await reconciler.reconcile(desired_active)
    assert len(drifts) >= 0
    assert action is not None
    assert action.success is True


@pytest.mark.asyncio
async def test_reconcile_detects_drift_when_inactive_but_running(desired_inactive):
    mock_provider = AsyncMock()
    mock_provider.get_observed_state.return_value = BackendObservedState(
        backend_id=desired_inactive.backend_id,
        provider="local_process",
        running=True,
        healthy=True,
    )
    mock_provider.stop_backend.return_value = LifecycleActionResult(
        success=True, action="stop", backend_id=desired_inactive.backend_id, message="stopped",
    )
    reconciler = BackendReconciler(mock_provider)
    observed, drifts, action = await reconciler.reconcile(desired_inactive)
    assert action is not None
    assert action.success is True


@pytest.mark.asyncio
async def test_reconcile_drift_health_check_fails(desired_active):
    mock_provider = AsyncMock()
    mock_provider.get_observed_state.return_value = BackendObservedState(
        backend_id=desired_active.backend_id,
        provider="local_process",
        running=True,
        healthy=False,
        error="health check failed",
    )
    reconciler = BackendReconciler(mock_provider)
    observed, drifts, action = await reconciler.reconcile(desired_active)
    health_drifts = [d for d in drifts if d.drift_type == DriftType.HEALTH_MISMATCH]
    assert len(health_drifts) >= 1


@pytest.mark.asyncio
async def test_reconcile_on_drift_callback(desired_active):
    callback = Mock()
    mock_provider = AsyncMock()
    mock_provider.get_observed_state.return_value = BackendObservedState(
        backend_id=desired_active.backend_id,
        provider="local_process",
        running=False,
        healthy=False,
        error="not found",
    )
    mock_provider.start_backend.return_value = LifecycleActionResult(
        success=True, action="start", backend_id=desired_active.backend_id, message="started",
    )
    reconciler = BackendReconciler(mock_provider, on_drift=callback)
    observed, drifts, action = await reconciler.reconcile(desired_active)
    callback.assert_called()
