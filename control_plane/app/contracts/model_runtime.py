from typing import Any, Dict, Optional, Protocol, runtime_checkable
from uuid import UUID

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel


class ModelInstance(BaseModel):
    id: UUID
    model_id: UUID
    backend_id: UUID
    status: str
    health_status: str
    port: int
    is_active: bool

class ModelRuntimeCapabilities(ContractCapability):
    hot_swap: bool = False
    multi_instance: bool = False
    automatic_health_checks: bool = False

@runtime_checkable
class ModelRuntimeContract(BaseContract, Protocol):
    """
    Contract for Model Runtime Management (Loading/Unloading/Monitoring models).
    """
    
    async def load_model(self, model_id: UUID, backend_id: UUID, model_path: str, runtime_config: Optional[Dict[str, Any]] = None) -> ModelInstance:
        """Loads a model into a new runtime instance."""
        ...

    async def unload_model(self, instance_id: UUID):
        """Unloads and terminates a model runtime instance."""
        ...

    async def activate_model(self, instance_id: UUID):
        """Sets a specific instance as the active one for a model/backend."""
        ...

    async def get_model_health(self, instance_id: UUID) -> Dict[str, Any]:
        """Returns health information for a model instance."""
        ...

    def capabilities(self) -> ModelRuntimeCapabilities:
        """Returns runtime management capabilities."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["load_model", "unload_model", "activate_model", "get_model_health", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
