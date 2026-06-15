from typing import Protocol, runtime_checkable
from uuid import UUID

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel


class BackendDesiredState(BaseModel):
    backend_id: UUID
    name: str
    provider: str
    backend_url: str
    is_active: bool
    status: str
    metadata_json: str | None = None


class BackendObservedState(BaseModel):
    backend_id: UUID
    provider: str
    running: bool
    healthy: bool
    pid: int | None = None
    container_id: str | None = None
    container_status: str | None = None
    pod_name: str | None = None
    pod_phase: str | None = None
    url: str | None = None
    error: str | None = None


class DriftRecord(BaseModel):
    backend_id: UUID
    backend_name: str
    drift_type: str
    desired: str
    observed: str
    timestamp: str


class LifecycleActionResult(BaseModel):
    success: bool
    action: str
    backend_id: UUID
    message: str
    error: str | None = None


class BackendLifecycleCapabilities(ContractCapability):
    can_start: bool = False
    can_stop: bool = False
    can_restart: bool = False
    can_observe: bool = True
    provider_type: str = "unknown"


@runtime_checkable
class BackendLifecycleContract(BaseContract, Protocol):
    async def get_observed_state(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> BackendObservedState: ...

    async def start_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult: ...

    async def stop_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult: ...

    async def restart_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult: ...

    def capabilities(self) -> BackendLifecycleCapabilities: ...

    def validate_contract(self) -> bool:
        required = [
            "get_observed_state",
            "start_backend",
            "stop_backend",
            "restart_backend",
            "capabilities",
        ]
        return all(hasattr(self, m) and callable(getattr(self, m)) for m in required)
