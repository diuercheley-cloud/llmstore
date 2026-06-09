from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.operations.remediation_execution import (
    RemediationExecution,
    RemediationExecutionStep,
    RemediationRollbackPlan,
    compute_deterministic_hash,
)
from app.services.operations.remediation_execution.audit_events import (
    log_remediation_execution_completed,
    log_remediation_execution_killed,
    log_remediation_execution_prepared,
    log_remediation_execution_started,
    log_remediation_execution_step_executed,
    log_remediation_execution_step_simulated,
)
from app.services.operations.remediation_execution.execution_gate import RemediationExecutionGate
from app.services.operations.remediation_execution.rollback import (
    RemediationRollbackPlanningService,
)
from app.services.operations.remediation_execution.simulation_adapter import (
    SimulatedRemediationExecutionAdapter,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ApprovalGatedRemediationExecutor:
    """
    Orchestrates the execution of remediation plans through safety gates.
    """

    def __init__(self):
        self.gate = RemediationExecutionGate()
        self.adapter = SimulatedRemediationExecutionAdapter()
        self.rollback_service = RemediationRollbackPlanningService()

    async def prepare_execution(self, db: AsyncSession, plan: Any, steps: List[Any], dry_run: bool = True) -> RemediationExecution:
        """
        Creates an execution record and a rollback plan.
        """
        # Build execution input hash
        input_data = {
            "plan_id": str(plan.id),
            "dry_run": dry_run,
            "step_ids": [str(s.id) for s in steps]
        }
        input_hash = compute_deterministic_hash(fields=input_data)
        
        # Check if already prepared
        stmt = select(RemediationExecution).where(RemediationExecution.input_hash == input_hash)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        execution = RemediationExecution(
            client_id=plan.client_id,
            plan_id=plan.id,
            execution_mode="real" if not dry_run else "simulation",
            dry_run=dry_run,
            status="pending",
            input_hash=input_hash,
            immutable_hash=compute_deterministic_hash(fields={**input_data, "client_id": str(plan.client_id)})
        )
        db.add(execution)
        await db.flush()

        # Create rollback plan
        rb_data = self.rollback_service.build_rollback_plan(plan.__dict__, [s.__dict__ for s in steps])
        rollback = RemediationRollbackPlan(
            client_id=plan.client_id,
            plan_id=plan.id,
            execution_id=execution.id,
            rollback_strategy=rb_data["rollback_strategy"],
            rollback_steps_json=rb_data["rollback_steps_json"],
            approval_required=rb_data["approval_required"],
            advisory_only=dry_run,
            dry_run=dry_run,
            immutable_hash=compute_deterministic_hash(fields={"execution_id": str(execution.id), "strategy": rb_data["rollback_strategy"]})
        )
        db.add(rollback)
        
        await log_remediation_execution_prepared(db, plan.client_id, execution.id, plan.id)
        
        return execution

    async def execute(self, db: AsyncSession, execution: RemediationExecution, plan: Any, steps: List[Any], 
                      approvals: List[Any], kill_switch_state: Optional[Any]) -> Dict[str, Any]:
        """
        Runs the simulation if gates pass.
        """
        if execution.status not in ["pending", "blocked"]:
            return {"error": f"Execution in invalid state: {execution.status}"}

        # Check gates
        gate_result = self.gate.can_execute(
            plan.__dict__, 
            [a.__dict__ for a in approvals],
            {"rollback_steps_json": [1]}, # Placeholder for check
            kill_switch_state.__dict__ if kill_switch_state else None,
            dry_run=execution.dry_run
        )
        
        execution.approval_verified = gate_result["approval_verified"]
        execution.blast_radius_checked = gate_result["blast_radius_checked"]
        execution.rollback_plan_present = gate_result["rollback_plan_present"]
        execution.kill_switch_checked = gate_result["kill_switch_checked"]

        if not gate_result["can_execute"]:
            execution.status = "blocked"
            await db.commit()
            return {"status": "blocked", "reasons": gate_result["reasons"]}

        # Start execution
        execution.status = "executing"
        execution.started_at = datetime.now(timezone.utc)
        await db.commit()
        await log_remediation_execution_started(db, execution.client_id, execution.id)

        step_results = []
        for p_step in steps:
            # Create execution step record
            exec_step = RemediationExecutionStep(
                client_id=execution.client_id,
                execution_id=execution.id,
                plan_step_id=p_step.id,
                step_order=p_step.step_order,
                action_type=p_step.action_type,
                target_domain=p_step.target_domain,
                target_ref=p_step.target_ref,
                dry_run=execution.dry_run,
                immutable_hash=compute_deterministic_hash(fields={"execution_id": str(execution.id), "plan_step_id": str(p_step.id)})
            )
            db.add(exec_step)
            await db.flush()

            # Execute via adapter
            sim_result = self.adapter.execute_step(p_step.__dict__, dry_run=execution.dry_run)
            exec_step.simulated_result_json = sim_result
            exec_step.execution_status = "completed"
            
            step_results.append(sim_result)
            await log_remediation_execution_step_executed(db, execution.client_id, exec_step.id, "success") if not execution.dry_run else log_remediation_execution_step_simulated(db, execution.client_id, exec_step.id, "success")

        execution.status = "completed" if not execution.dry_run else "dry_run_completed"
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await log_remediation_execution_completed(db, execution.client_id, execution.id)

        return {
            "execution_id": execution.id,
            "status": execution.status,
            "step_results": step_results
        }

    async def kill_execution(self, db: AsyncSession, execution: RemediationExecution, reason: str):
        """
        Emergency stop.
        """
        if execution.status in ["completed", "failed", "killed"]:
            return
            
        execution.status = "killed"
        execution.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await log_remediation_execution_killed(db, execution.client_id, execution.id, reason)

    def explain_execution(self, execution: RemediationExecution) -> str:
        return f"Remediation Execution {execution.id} - Mode: {execution.execution_mode} - Status: {execution.status} - Dry Run: {execution.dry_run}"
