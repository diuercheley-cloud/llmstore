import logging
import uuid
import httpx
from typing import Dict, Any
from app.services.routing.infra_adapters.base import BaseInfraAdapter
from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class NomadAdapter(BaseInfraAdapter):
    def __init__(self):
        self.settings = get_settings()

    def validate_connection(self) -> bool:
        if not self.settings.commercial_nomad_execution_enabled:
            return False
        if not self.settings.commercial_nomad_addr:
            return False
        return True

    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> Dict[str, Any]:
        return {
            "adapter": "nomad",
            "addr": self.settings.commercial_nomad_addr,
            "target": simulation.target_identifier,
            "action": simulation.simulation_type,
            "dry_run": True
        }

    async def execute_action(self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True) -> Dict[str, Any]:
        if not self.validate_connection():
            return {"status": "failed", "error": "Nomad adapter unavailable or disabled"}

        effective_dry_run = dry_run or self.settings.commercial_nomad_dry_run
        
        try:
            action = simulation.simulation_type
            job_id = simulation.target_identifier
            details = simulation.requested_action_json

            if action in ["scale_up", "scale_down"]:
                count = details.get("count") or details.get("nodes") or details.get("replicas")
                group = details.get("group", "default")
                
                if count is None:
                    return {"status": "failed", "error": "Count not specified for scaling"}

                if effective_dry_run:
                    return {
                        "status": "dry_run",
                        "external_id": f"nomad-dryrun-{uuid.uuid4()}",
                        "message": f"Dry run: Scale Nomad job {job_id} group {group} to {count}"
                    }

                # Nomad Scaling via API
                # https://www.nomadproject.io/api-docs/jobs#scale-job
                async with httpx.AsyncClient() as client:
                    headers = {}
                    if self.settings.commercial_nomad_token:
                        headers["X-Nomad-Token"] = self.settings.commercial_nomad_token
                    
                    url = f"{self.settings.commercial_nomad_addr}/v1/job/{job_id}/scale"
                    payload = {
                        "JobID": job_id,
                        "TaskGroups": {
                            group: {
                                "Count": count
                            }
                        }
                    }
                    
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        res_data = response.json()
                        return {
                            "status": "executed",
                            "external_id": res_data.get("EvalID", str(uuid.uuid4())),
                            "message": f"Successfully scaled Nomad job {job_id}"
                        }
                    else:
                        return {
                            "status": "failed",
                            "error": f"Nomad API error: {response.status_code} {response.text}"
                        }

            return {"status": "failed", "error": f"Action {action} not supported by Nomad adapter"}

        except Exception as e:
            logger.error(f"Nomad execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def rollback_action(self, execution_record_id: str) -> Dict[str, Any]:
        return {
            "status": "failed",
            "message": "Rollback not fully implemented for Nomad."
        }

    async def get_status(self, external_operation_id: str) -> Dict[str, Any]:
        return {"status": "unknown", "external_id": external_operation_id}
