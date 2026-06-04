from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel, Field


class PlatformEvent(BaseModel):
    event_type: str
    severity: str
    title: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_id: Optional[str] = None
    request_id: Optional[str] = None

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

    async def list_events(self, limit: int = 100) -> List[PlatformEvent]:
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
