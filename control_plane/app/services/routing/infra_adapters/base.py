from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation


class BaseInfraAdapter(ABC):
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validates connection to the target infrastructure."""
        pass

    @abstractmethod
    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> Dict[str, Any]:
        """Plans an action based on a simulation, returning details for execution."""
        pass

    @abstractmethod
    async def execute_action(self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True) -> Dict[str, Any]:
        """Executes an action from a simulation."""
        pass

    @abstractmethod
    async def rollback_action(self, execution_record_id: str) -> Dict[str, Any]:
        """Attempts to rollback an execution."""
        pass

    @abstractmethod
    async def get_status(self, external_operation_id: str) -> Dict[str, Any]:
        """Gets status of an external operation."""
        pass
