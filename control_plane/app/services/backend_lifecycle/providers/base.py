from uuid import UUID

from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendLifecycleContract,
    BackendObservedState,
    LifecycleActionResult,
)


class ProviderUnavailableError(Exception):
    def __init__(self, provider: str, detail: str = ""):
        self.provider = provider
        self.detail = detail
        super().__init__(f"provider {provider} unavailable: {detail}")


class BaseLifecycleProvider(BackendLifecycleContract):
    async def get_observed_state(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> BackendObservedState:
        raise NotImplementedError

    async def start_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        raise ProviderUnavailableError(self.__class__.__name__, "start not supported")

    async def stop_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        raise ProviderUnavailableError(self.__class__.__name__, "stop not supported")

    async def restart_backend(
        self, backend_id: UUID, desired: BackendDesiredState
    ) -> LifecycleActionResult:
        raise ProviderUnavailableError(self.__class__.__name__, "restart not supported")

    def capabilities(self) -> BackendLifecycleCapabilities:
        return BackendLifecycleCapabilities()

    def validate_contract(self) -> bool:
        return True
