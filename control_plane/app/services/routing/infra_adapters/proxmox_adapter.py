import logging
from typing import Any

import requests
from app.core.config import get_settings
from app.models.commercial.commercial_infra_simulation import CommercialInfrastructureSimulation
from app.services.routing.infra_adapters.base import BaseInfraAdapter

logger = logging.getLogger(__name__)


class ProxmoxAdapter(BaseInfraAdapter):
    def __init__(self):
        self.settings = get_settings()

    def _get_headers(self) -> dict[str, str]:
        if (
            not self.settings.commercial_proxmox_token_id
            or not self.settings.commercial_proxmox_token_secret
        ):
            return {}
        # Secret is never logged due to this being a private helper
        return {
            "Authorization": f"PVEAPIToken={self.settings.commercial_proxmox_token_id}={self.settings.commercial_proxmox_token_secret}"
        }

    def validate_connection(self) -> bool:
        if not self.settings.commercial_proxmox_execution_enabled:
            return False
        if not self.settings.commercial_proxmox_api_url:
            return False

        try:
            url = f"{self.settings.commercial_proxmox_api_url.rstrip('/')}/api2/json/version"
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=self.settings.commercial_proxmox_verify_tls,
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            # Token is not in URL or headers logged here
            logger.error("Proxmox connection validation failed")
            return False

    async def plan_action(self, simulation: CommercialInfrastructureSimulation) -> dict[str, Any]:
        return {
            "adapter": "proxmox",
            "action": simulation.simulation_type,
            "target": simulation.target_identifier,
            "planned_at": str(simulation.created_at),
        }

    async def execute_action(
        self, simulation: CommercialInfrastructureSimulation, dry_run: bool = True
    ) -> dict[str, Any]:
        if not self.settings.commercial_proxmox_execution_enabled:
            return {"status": "failed", "error": "Proxmox execution disabled"}

        action = simulation.simulation_type
        vmid = simulation.target_identifier

        # Check allowlist
        allowed_vms = [
            x.strip()
            for x in self.settings.commercial_proxmox_allowed_vm_ids.split(",")
            if x.strip()
        ]
        allowed_cts = [
            x.strip()
            for x in self.settings.commercial_proxmox_allowed_ct_ids.split(",")
            if x.strip()
        ]

        if vmid not in allowed_vms and vmid not in allowed_cts:
            return {"status": "failed", "error": f"VM/CT {vmid} not in allowlist"}

        effective_dry_run = dry_run or self.settings.commercial_proxmox_dry_run

        if effective_dry_run:
            return {"status": "dry_run", "action": action, "vmid": vmid}

        # Real execution logic
        if action == "start_vm":
            return self._vm_action(vmid, "status/start")
        elif action == "stop_vm":
            return self._vm_action(vmid, "status/stop")
        elif action == "restart_vm":
            return self._vm_action(vmid, "status/reboot")
        elif action == "inspect_vm":
            return self._vm_action(vmid, "status/current", method="get")
        else:
            return {"status": "failed", "error": f"Unsupported Proxmox action: {action}"}

    def _vm_action(self, vmid: str, path: str, method: str = "post") -> dict[str, Any]:
        node = self.settings.commercial_proxmox_node
        if not node:
            return {"status": "failed", "error": "Proxmox node not configured"}

        # Detect if CT or VM
        allowed_cts = [
            x.strip()
            for x in self.settings.commercial_proxmox_allowed_ct_ids.split(",")
            if x.strip()
        ]
        is_ct = vmid in allowed_cts
        type_path = "lxc" if is_ct else "qemu"

        url = f"{self.settings.commercial_proxmox_api_url.rstrip('/')}/api2/json/nodes/{node}/{type_path}/{vmid}/{path}"

        try:
            if method == "post":
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    verify=self.settings.commercial_proxmox_verify_tls,
                    timeout=30,
                )
            else:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    verify=self.settings.commercial_proxmox_verify_tls,
                    timeout=30,
                )

            if response.status_code in [200, 202]:
                return {
                    "status": "executed",
                    "external_id": response.json().get("data"),
                    "response": response.json(),
                }
            else:
                return {"status": "failed", "error": f"Proxmox API error: {response.status_code}"}
        except Exception:
            return {"status": "failed", "error": "Proxmox request failed"}

    async def rollback_action(self, execution_record_id: str) -> dict[str, Any]:
        return {"status": "skipped", "message": "Rollback not implemented for Proxmox yet"}

    async def get_status(self, external_operation_id: str) -> dict[str, Any]:
        return {"status": "unknown", "external_id": external_operation_id}

    def get_capacity(self) -> dict[str, Any]:
        if not self.validate_connection():
            return {"status": "unavailable"}

        node = self.settings.commercial_proxmox_node
        url = (
            f"{self.settings.commercial_proxmox_api_url.rstrip('/')}/api2/json/nodes/{node}/status"
        )

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=self.settings.commercial_proxmox_verify_tls,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "status": "available",
                    "cpu_usage": data.get("cpu"),
                    "memory_total": data.get("memory", {}).get("total"),
                    "memory_used": data.get("memory", {}).get("used"),
                    "uptime": data.get("uptime"),
                }
        except Exception:
            pass
        return {"status": "error"}
