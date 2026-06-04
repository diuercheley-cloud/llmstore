import logging
import shutil
import subprocess
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.models.commercial_infra_simulation import CommercialInfrastructureSimulation
from app.services.routing.infra_adapters.base import BaseInfraAdapter

logger = logging.getLogger(__name__)

class LocalGPUAdapter(BaseInfraAdapter):
    def __init__(self):
        self.settings = get_settings()

    def _has_nvidia_smi(self) -> bool:
        return shutil.which("nvidia-smi") is not None

    def validate_connection(self) -> bool:
        if not self.settings.commercial_local_gpu_execution_enabled:
            return False
        return self._has_nvidia_smi()

    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> Dict[str, Any]:
        return {
            "adapter": "local_gpu",
            "action": simulation.simulation_type,
            "target": simulation.target_identifier,
            "planned_at": str(simulation.created_at)
        }

    async def execute_action(self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True) -> Dict[str, Any]:
        if not self.settings.commercial_local_gpu_execution_enabled:
            return {"status": "failed", "error": "Local GPU execution disabled"}

        action = simulation.simulation_type
        allowed_actions = [x.strip() for x in self.settings.commercial_local_gpu_allowed_actions.split(",") if x.strip()]
        
        if action not in allowed_actions:
            return {"status": "failed", "error": f"Action {action} not in allowed_actions"}

        effective_dry_run = dry_run or self.settings.commercial_local_gpu_dry_run
        
        if action == "inspect":
            return self.inspect_gpu()
        elif action == "metrics":
            return self.collect_gpu_metrics()
        
        # Actions requiring non-dry-run and explicit permission
        if effective_dry_run:
            return {"status": "dry_run", "action": action}

        if action == "power_limit":
            if not self.settings.commercial_local_gpu_allow_power_limit:
                return {"status": "failed", "error": "Power limit adjustment disabled"}
            return self.apply_power_limit(simulation.requested_action_json.get("limit_watts"))
        
        if action == "kill_process":
            if not self.settings.commercial_local_gpu_allow_process_kill:
                return {"status": "failed", "error": "Process kill disabled"}
            return self.kill_gpu_process(simulation.requested_action_json.get("pid"))

        if action == "service_restart":
            if not self.settings.commercial_local_gpu_allow_service_restart:
                return {"status": "failed", "error": "Service restart disabled"}
            return self.restart_local_inference_service()

        return {"status": "failed", "error": f"Unsupported or blocked action: {action}"}

    def inspect_gpu(self) -> Dict[str, Any]:
        if not self._has_nvidia_smi():
            return {"status": "unavailable"}
        
        try:
            # Safe command execution - no shell=True
            cmd = ["nvidia-smi", "-L"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return {"status": "executed", "output": result.stdout.strip()}
            return {"status": "failed", "error": "nvidia-smi error"}
        except Exception:
            return {"status": "failed", "error": "GPU inspection failed"}

    def collect_gpu_metrics(self) -> Dict[str, Any]:
        if not self._has_nvidia_smi():
            return {"status": "unavailable"}
        
        try:
            # Query specific fields in CSV format
            query = "index,name,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,temperature.gpu,power.draw"
            cmd = ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                gpus = []
                for line in lines:
                    vals = [v.strip() for v in line.split(",")]
                    if len(vals) >= 9:
                        try:
                            gpus.append({
                                "index": vals[0],
                                "name": vals[1],
                                "utilization_gpu": float(vals[2]),
                                "utilization_memory": float(vals[3]),
                                "memory_total": float(vals[4]),
                                "memory_used": float(vals[5]),
                                "memory_free": float(vals[6]),
                                "temperature": float(vals[7]),
                                "power_draw": float(vals[8])
                            })
                        except (ValueError, IndexError):
                            continue
                return {"status": "executed", "gpus": gpus}
            return {"status": "failed", "error": "nvidia-smi metrics failed"}
        except Exception:
            return {"status": "failed", "error": "GPU metrics collection failed"}

    def apply_power_limit(self, limit_watts: Optional[int]) -> Dict[str, Any]:
        if not limit_watts:
            return {"status": "failed", "error": "Missing limit_watts"}
        
        try:
            cmd = ["nvidia-smi", "-pl", str(limit_watts)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"status": "executed", "output": result.stdout.strip()}
            return {"status": "failed", "error": "nvidia-smi power limit failed"}
        except Exception:
            return {"status": "failed", "error": "Power limit application failed"}

    def kill_gpu_process(self, pid: Optional[int]) -> Dict[str, Any]:
        # Strictly blocked for now unless explicitly enabled AND requested
        return {"status": "failed", "error": "GPU process kill is strictly blocked in this phase"}

    def restart_local_inference_service(self) -> Dict[str, Any]:
        # Mocking for now, as it depends on the supervisor (systemd, docker, etc.)
        return {"status": "failed", "error": "Service restart not implemented"}

    async def rollback_action(self, execution_record_id: str) -> Dict[str, Any]:
        return {"status": "skipped"}

    async def get_status(self, external_operation_id: str) -> Dict[str, Any]:
        return {"status": "completed"}
