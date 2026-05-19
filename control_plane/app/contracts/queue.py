from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from app.contracts.base import BaseContract, ContractCapability
from contextlib import asynccontextmanager

class QueueSnapshot(BaseModel):
    queues: Dict[str, Dict[str, Any]]
    total_pending: int

class QueueCapabilities(ContractCapability):
    priority_queues: bool = False
    per_backend_limits: bool = False
    fairness_scheduling: bool = False

@runtime_checkable
class QueueContract(BaseContract, Protocol):
    """
    Contract for Request Queuing and Concurrency Control.
    """
    
    @asynccontextmanager
    async def slot(self, plan_code: str = "free", is_admin: bool = False, backend_id: Optional[str] = None):
        """Acquires a concurrency slot for a request."""
        ...

    def get_snapshot(self) -> QueueSnapshot:
        """Returns the current state of all queues."""
        ...

    def capabilities(self) -> QueueCapabilities:
        """Returns queuing capabilities."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["slot", "get_snapshot", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method):
                return False
        return True
