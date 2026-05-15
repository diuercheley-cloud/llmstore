import uuid
import logging
from typing import Dict, Any
from app.services.routing.infra_adapters.base import BaseInfraAdapter
from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation

logger = logging.getLogger(__name__)

class MockAdapter(BaseInfraAdapter):
    def validate_connection(self) -> bool:
        return True

    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> Dict[str, Any]:
        return {
            "adapter": "mock",
            "plan_id": str(uuid.uuid4()),
            "action": simulation.simulation_type,
            "target": simulation.target_identifier,
            "details": simulation.requested_action_json
        }

    async def execute_action(self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True) -> Dict[str, Any]:
        logger.info(f"Mock execution: {simulation.simulation_type} on {simulation.target_identifier} (dry_run={dry_run})")
        return {
            "status": "dry_run" if dry_run else "executed",
            "external_id": f"mock-{uuid.uuid4()}",
            "message": f"Successfully simulated {simulation.simulation_type}"
        }

    async def rollback_action(self, execution_record_id: str) -> Dict[str, Any]:
        logger.info(f"Mock rollback: {execution_record_id}")
        return {
            "status": "rolled_back",
            "message": "Successfully rolled back mock action"
        }

    async def get_status(self, external_operation_id: str) -> Dict[str, Any]:
        return {
            "status": "completed",
            "external_id": external_operation_id
        }
