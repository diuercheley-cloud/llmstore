from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel, Field


class PlatformEvent(BaseModel):
    event_type: str
    severity: str
    title: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    client_id: str | None = None
    request_id: str | None = None


class EventCapabilities(ContractCapability):
    async_logging: bool = False
    persistence: bool = False
    realtime_streaming: bool = False


@runtime_checkable
class EventContract(BaseContract, Protocol):
    """
    Contract for Platform Event Logging.
    """

    async def log_event(self, event: PlatformEvent) -> bool:
        """Logs a platform event."""
        ...

    async def list_events(self, limit: int = 100) -> list[PlatformEvent]:
        """Lists recent platform events."""
        ...

    def capabilities(self) -> EventCapabilities:
        """Returns event logging capabilities."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["log_event", "list_events", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
