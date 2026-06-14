from uuid import uuid4

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendObservedState,
    DriftRecord,
    LifecycleActionResult,
)


def test_desired_state_roundtrip():
    backend_id = uuid4()
    state = BackendDesiredState(
        backend_id=backend_id,
        name="test-backend",
        provider="llama.cpp",
        backend_url="http://localhost:8080",
        is_active=True,
        status="running",
        metadata_json='{"service_name": "test"}',
    )
    dumped = state.model_dump()
    assert dumped["backend_id"] == backend_id
    assert dumped["name"] == "test-backend"
    assert dumped["provider"] == "llama.cpp"
    assert dumped["is_active"] is True
    assert dumped["status"] == "running"


def test_observed_state_defaults():
    backend_id = uuid4()
    state = BackendObservedState(
        backend_id=backend_id,
        provider="docker",
        running=True,
        healthy=True,
    )
    assert state.running is True
    assert state.healthy is True
    assert state.pid is None
    assert state.container_id is None
    assert state.error is None


def test_drift_record():
    drift = DriftRecord(
        backend_id=uuid4(),
        backend_name="test",
        drift_type="status_mismatch",
        desired="running",
        observed="stopped",
        timestamp="2026-01-01T00:00:00Z",
    )
    assert drift.drift_type == "status_mismatch"


def test_lifecycle_action_result():
    result = LifecycleActionResult(
        success=True,
        action="start",
        backend_id=uuid4(),
        message="started",
    )
    assert result.success is True
    assert result.error is None


def test_lifecycle_action_result_with_error():
    result = LifecycleActionResult(
        success=False,
        action="start",
        backend_id=uuid4(),
        message="failed",
        error="provider unavailable",
    )
    assert result.success is False
    assert result.error == "provider unavailable"


def test_capabilities_defaults():
    caps = BackendLifecycleCapabilities()
    assert caps.can_start is False
    assert caps.can_stop is False
    assert caps.can_restart is False
    assert caps.can_observe is True
    assert caps.provider_type == "unknown"


def test_desired_state_from_existing():
    backend_id = uuid4()
    state = BackendDesiredState(
        backend_id=backend_id,
        name="vllm-local",
        provider="vllm",
        backend_url="http://localhost:8000",
        is_active=False,
        status="stopped",
    )
    assert state.is_active is False
    assert state.status == "stopped"
