import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_infra_simulation import (
    CommercialApprovalRecord,
    CommercialExecutionRecord,
    CommercialInfrastructureSimulation,
)
from app.models.core.admin_action_log import AdminActionLog
from app.services.routing.commercial_leader_election import _active_lease_query, is_current_leader
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.routing.infra_adapters.kubernetes_adapter import KubernetesAdapter
from app.services.routing.infra_adapters.local_gpu_adapter import LocalGPUAdapter
from app.services.routing.infra_adapters.mock_adapter import MockAdapter
from app.services.routing.infra_adapters.nomad_adapter import NomadAdapter
from app.services.routing.infra_adapters.proxmox_adapter import ProxmoxAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CommercialInfraExecutionService:
    def __init__(self):
        self.settings = get_settings()
        self.adapters = {
            "mock": MockAdapter(),
            "kubernetes": KubernetesAdapter(),
            "nomad": NomadAdapter(),
            "proxmox": ProxmoxAdapter(),
            "local_gpu": LocalGPUAdapter(),
        }

    def get_adapter(self, name: str):
        return self.adapters.get(name)

    async def list_adapters(self) -> list[dict[str, Any]]:
        enabled_adapters = self.settings.commercial_infra_adapters_enabled.split(",")
        result = []
        for name, adapter in self.adapters.items():
            adapter_info = {
                "name": name,
                "enabled": name in enabled_adapters,
                "connected": adapter.validate_connection(),
                "dry_run": True,
                "capabilities": [],
                "risks": "low",
            }

            if name == "proxmox":
                adapter_info["dry_run"] = self.settings.commercial_proxmox_dry_run
                adapter_info["capabilities"] = [
                    "start_vm",
                    "stop_vm",
                    "restart_vm",
                    "inspect_vm",
                    "capacity",
                ]
                adapter_info["risks"] = "medium"
            elif name == "local_gpu":
                adapter_info["dry_run"] = self.settings.commercial_local_gpu_dry_run
                adapter_info["capabilities"] = [
                    "inspect",
                    "metrics",
                    "power_limit",
                    "process_kill",
                    "service_restart",
                ]
                adapter_info["risks"] = "high"
            elif name == "kubernetes":
                adapter_info["dry_run"] = self.settings.commercial_k8s_dry_run
                adapter_info["capabilities"] = ["scale", "restart", "logs"]
            elif name == "nomad":
                adapter_info["dry_run"] = self.settings.commercial_nomad_dry_run
                adapter_info["capabilities"] = ["scale", "restart"]

            result.append(adapter_info)
        return result

    async def validate_execution_preconditions(
        self,
        db: AsyncSession,
        simulation: CommercialInfrastructureSimulation,
        dry_run: bool,
        confirm: bool = False,
    ) -> dict[str, Any]:
        if not self.settings.commercial_infra_execution_enabled:
            return {"allowed": False, "reason": "Infrastructure execution is globally disabled"}

        if not dry_run and self.settings.commercial_infra_execution_mode == "simulation_only":
            return {"allowed": False, "reason": "System is in simulation_only mode"}

        # Check safety gate
        if simulation.safety_gate_status == "blocked":
            return {"allowed": False, "reason": "Simulation was blocked by safety gates"}

        # Check approval
        if self.settings.commercial_infra_require_approval and not dry_run:
            stmt = select(CommercialApprovalRecord).where(
                CommercialApprovalRecord.simulation_id == simulation.id,
                CommercialApprovalRecord.status == "approved",
            )
            result = await db.execute(stmt)
            approval = result.scalars().first()
            if not approval:
                return {"allowed": False, "reason": "Action requires approved manual record"}

        # Check Leader
        if self.settings.commercial_infra_require_leader and not dry_run:
            is_leader = await is_current_leader(
                db,
                cluster_id=self.settings.commercial_cluster_id,
                leader_role="global",
                node_id=self.settings.node_id,
            )
            if not is_leader:
                return {"allowed": False, "reason": "Node is not the current cluster leader"}

        # Check confirm for real execution
        if not dry_run and not confirm:
            return {"allowed": False, "reason": "Real execution requires explicit confirmation"}

        return {"allowed": True}

    async def execute_simulation(
        self,
        db: AsyncSession,
        simulation_id: uuid.UUID,
        adapter_name: str,
        dry_run: bool = True,
        confirm: bool = False,
        approval_id: uuid.UUID | None = None,
    ) -> CommercialExecutionRecord:
        simulation = await db.get(CommercialInfrastructureSimulation, simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        preconditions = await self.validate_execution_preconditions(
            db, simulation, dry_run, confirm
        )
        if not preconditions["allowed"]:
            # Record blocked execution
            record = CommercialExecutionRecord(
                id=uuid.uuid4(),
                simulation_id=simulation.id,
                approval_id=approval_id,
                adapter=adapter_name,
                action_type=simulation.simulation_type,
                target_scope=simulation.target_scope,
                target_identifier=simulation.target_identifier,
                requested_action_json=simulation.requested_action_json,
                status="blocked",
                dry_run=dry_run,
                error_message=preconditions["reason"],
                created_at=utc_now(),
            )
            db.add(record)

            audit = AdminActionLog(
                id=uuid.uuid4(),
                action="infra_execution_blocked",
                admin_role="system",
                payload_json={
                    "simulation_id": str(simulation_id),
                    "reason": preconditions["reason"],
                },
                status="blocked",
                created_at=utc_now(),
            )
            db.add(audit)

            await db.commit()
            return record

        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Adapter {adapter_name} not found")

        # Get leader and fencing tokens if required
        leader_node_id = None
        fencing_token = None
        if self.settings.commercial_infra_require_leader:
            leader_node_id = self.settings.node_id
            if self.settings.commercial_infra_require_fencing:
                lease = await _active_lease_query(
                    db, cluster_id=self.settings.commercial_cluster_id, leader_role="global"
                )
                if lease:
                    fencing_token = str(lease.id)

        record = CommercialExecutionRecord(
            id=uuid.uuid4(),
            simulation_id=simulation.id,
            approval_id=approval_id,
            adapter=adapter_name,
            action_type=simulation.simulation_type,
            target_scope=simulation.target_scope,
            target_identifier=simulation.target_identifier,
            requested_action_json=simulation.requested_action_json,
            status="pending",
            dry_run=dry_run,
            leader_node_id=leader_node_id,
            fencing_token=fencing_token,
            created_at=utc_now(),
        )
        db.add(record)

        audit_start = AdminActionLog(
            id=uuid.uuid4(),
            action="infra_execution_started",
            admin_role="admin",
            payload_json={
                "simulation_id": str(simulation_id),
                "adapter": adapter_name,
                "dry_run": dry_run,
                "action": simulation.simulation_type,
            },
            status="pending",
            created_at=utc_now(),
        )
        db.add(audit_start)

        await db.flush()

        try:
            result = await adapter.execute_action(simulation, dry_run=dry_run)
            sanitized_result = sanitize_report_payload(result)
            record.status = result.get("status", "executed")
            record.external_operation_id = result.get("external_id")
            record.result_json = sanitized_result
            record.error_message = result.get("error")
            record.executed_at = utc_now()

            audit_end = AdminActionLog(
                id=uuid.uuid4(),
                action="infra_execution_success"
                if record.status in ["executed", "dry_run"]
                else "infra_execution_failed",
                admin_role="admin",
                payload_json={"execution_id": str(record.id), "status": record.status},
                status=record.status,
                created_at=utc_now(),
            )
            db.add(audit_end)

        except Exception as e:
            logger.error(f"Execution failed for simulation {simulation_id}: {e}")
            record.status = "failed"
            record.error_message = str(e)
            record.executed_at = utc_now()

            audit_fail = AdminActionLog(
                id=uuid.uuid4(),
                action="infra_execution_failed",
                admin_role="admin",
                payload_json={"execution_id": str(record.id), "error": str(e)},
                status="failed",
                created_at=utc_now(),
            )
            db.add(audit_fail)

        await db.commit()
        return record

    async def rollback_execution(
        self, db: AsyncSession, execution_id: uuid.UUID
    ) -> CommercialExecutionRecord:
        record = await db.get(CommercialExecutionRecord, execution_id)
        if not record:
            raise ValueError(f"Execution record {execution_id} not found")

        if record.status == "rolled_back":
            return record

        adapter = self.get_adapter(record.adapter)
        if not adapter:
            raise ValueError(f"Adapter {record.adapter} not found")

        try:
            result = await adapter.rollback_action(str(record.id))
            if result.get("status") == "rolled_back":
                record.status = "rolled_back"
                record.result_json = {**(record.result_json or {}), "rollback_result": result}

                audit = AdminActionLog(
                    id=uuid.uuid4(),
                    action="infra_execution_rollback",
                    admin_role="admin",
                    payload_json={"execution_id": str(execution_id)},
                    status="rolled_back",
                    created_at=utc_now(),
                )
                db.add(audit)
            else:
                record.error_message = f"Rollback failed: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Rollback failed for execution {execution_id}: {e}")
            record.error_message = f"Rollback exception: {str(e)}"

        await db.commit()
        return record


_execution_service = None


def get_infra_execution_service() -> CommercialInfraExecutionService:
    global _execution_service
    if _execution_service is None:
        _execution_service = CommercialInfraExecutionService()
    return _execution_service
