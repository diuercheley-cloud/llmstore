import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.managed_control_plane import ApplianceEnrollRequest, ApplianceHeartbeatPayload
from app.services.managed_control_plane import ManagedControlPlaneService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_invalid_enrollment_token_returns_none():
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(None)

    service = ManagedControlPlaneService(session)
    result = await service.enroll_appliance(
        ApplianceEnrollRequest(
            enrollment_token="invalid-token",
            appliance_external_id="app-456",
            name="Should Fail",
        )
    )

    assert result is None


@pytest.mark.asyncio
async def test_record_heartbeat_rejects_revoked_appliance():
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(SimpleNamespace(status="revoked"))

    service = ManagedControlPlaneService(session)
    accepted = await service.record_heartbeat(
        uuid.uuid4(),
        ApplianceHeartbeatPayload(
            version="1.0.0",
            health_status="healthy",
            readiness=True,
            capacity_summary={"gpu_free_mb": 1024, "queue_depth": 0},
            enabled_providers=["ollama"],
            available_models=["llama3"],
        ),
    )

    assert accepted is False


def test_managed_heartbeat_payload_only_accepts_operational_metadata():
    payload = ApplianceHeartbeatPayload(
        version="1.0.0",
        health_status="healthy",
        readiness=True,
        capacity_summary={"gpu_free_mb": 1024, "queue_depth": 0, "node_ready": True},
        enabled_providers=["ollama"],
        available_models=["llama3"],
    )

    assert payload.capacity_summary["gpu_free_mb"] == 1024

    with pytest.raises(ValueError, match="capacity_summary key 'document' is not allowed"):
        ApplianceHeartbeatPayload(
            version="1.0.0",
            health_status="healthy",
            readiness=True,
            capacity_summary={"document": "sensitive content"},
            enabled_providers=["ollama"],
            available_models=["llama3"],
        )
