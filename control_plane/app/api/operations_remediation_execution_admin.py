# Owner: platform-ops
import uuid
from typing import Any, List, Optional

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.remediation_execution import (
    RemediationExecution,
    RemediationExecutionReceipt,
    RemediationKillSwitchState,
    RemediationRollbackPlan,
    compute_deterministic_hash,
)
from app.models.operations.remediation_planning import (
    RemediationApprovalRequirement,
    RemediationPlan,
    RemediationStep,
)
from app.services.operations.remediation_execution.audit_events import (
    log_remediation_kill_switch_updated,
)
from app.services.operations.remediation_execution.executor import ApprovalGatedRemediationExecutor
from app.services.operations.remediation_execution.receipts import (
    build_post_execution_receipt,
    build_pre_execution_receipt,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
EXECUTOR = ApprovalGatedRemediationExecutor()

# --- Schemas ---

class RemediationExecutionPrepareRequest(BaseModel):
    client_id: uuid.UUID
    plan_id: uuid.UUID
    dry_run: bool = True
    idempotency_key: Optional[str] = None

class RemediationExecutionRequest(BaseModel):
    client_id: uuid.UUID
    execution_id: uuid.UUID
    dry_run: bool = True
    # In real execution, dry_run should match what was prepared, but we allow override if safe.

class RemediationKillSwitchUpdateRequest(BaseModel):
    client_id: uuid.UUID
    enabled: bool
    reason: str

# --- Endpoints ---

@router.post("/prepare")
async def prepare_remediation_execution(
    payload: RemediationExecutionPrepareRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Prepares execution for a given plan."""
    # 1. Fetch plan and steps
    stmt_plan = select(RemediationPlan).where(RemediationPlan.id == payload.plan_id)
    plan = (await db.execute(stmt_plan)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if plan.client_id != payload.client_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")

    stmt_steps = select(RemediationStep).where(RemediationStep.plan_id == payload.plan_id).order_by(RemediationStep.step_order.asc())
    steps = (await db.execute(stmt_steps)).scalars().all()
    
    # 2. Prepare via executor
    execution = await EXECUTOR.prepare_execution(
        db, 
        plan, 
        list(steps), 
        requested_by=_admin.get("username", "system"),
        dry_run=payload.dry_run,
        idempotency_key=payload.idempotency_key
    )
    await db.commit()
    
    # 3. Generate pre-execution receipt
    receipt_data = build_pre_execution_receipt({
        "id": str(execution.id),
        "client_id": str(execution.client_id),
        "plan_id": str(execution.plan_id),
        "deterministic_version": execution.deterministic_version,
        "dry_run": execution.dry_run
    })
    
    receipt = RemediationExecutionReceipt(
        client_id=execution.client_id,
        execution_id=execution.id,
        receipt_type=receipt_data["receipt_type"],
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    await db.commit()
    
    return {
        "execution": execution,
        "receipt": receipt
    }

@router.post("/execute")
async def execute_remediation(
    payload: RemediationExecutionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Executes a prepared remediation (simulated in Phase 72)."""
    # 1. Fetch execution
    stmt_exec = select(RemediationExecution).where(RemediationExecution.id == payload.execution_id)
    execution = (await db.execute(stmt_exec)).scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if execution.client_id != payload.client_id:
        raise HTTPException(status_code=403, detail="Tenant isolation violation")

    # 2. Fetch context for gates
    stmt_plan = select(RemediationPlan).where(RemediationPlan.id == execution.plan_id)
    plan = (await db.execute(stmt_plan)).scalar_one()
    
    stmt_steps = select(RemediationStep).where(RemediationStep.plan_id == plan.id).order_by(RemediationStep.step_order.asc())
    steps = (await db.execute(stmt_steps)).scalars().all()
    
    stmt_approvals = select(RemediationApprovalRequirement).where(RemediationApprovalRequirement.plan_id == plan.id)
    approvals_reqs = (await db.execute(stmt_approvals)).scalars().all()
    
    # In real execution, we don't pass mock_approvals. 
    # The executor's gate will check the CriticalApproval table.
    # We pass approvals_reqs just in case it needs the requirement definitions.
    
    stmt_ks = select(RemediationKillSwitchState).where(RemediationKillSwitchState.client_id == payload.client_id)
    ks_state = (await db.execute(stmt_ks)).scalar_one_or_none()
    
    # 3. Execute
    # Ensure dry_run consistency if not overridden explicitly in payload
    execution.dry_run = payload.dry_run
    
    result = await EXECUTOR.execute(db, execution, plan, list(steps), [r.__dict__ for r in approvals_reqs], ks_state)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    if result.get("status") == "blocked":
        return result

    # 4. Generate post-execution receipt
    receipt_data = build_post_execution_receipt({
        "id": str(execution.id),
        "client_id": str(execution.client_id),
        "status": execution.status,
        "dry_run": execution.dry_run
    }, result["step_results"])
    
    receipt = RemediationExecutionReceipt(
        client_id=execution.client_id,
        execution_id=execution.id,
        receipt_type=receipt_data["receipt_type"],
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    await db.commit()
    
    return {
        "execution": execution,
        "step_results": result["step_results"],
        "receipt": receipt
    }

@router.get("/")
async def list_remediation_executions(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Lists executions for a client."""
    stmt = select(RemediationExecution).where(RemediationExecution.client_id == client_id).order_by(RemediationExecution.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/kill-switch")
async def update_remediation_kill_switch(
    payload: RemediationKillSwitchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Enables or disables the remediation kill-switch for a client."""
    stmt = select(RemediationKillSwitchState).where(RemediationKillSwitchState.client_id == payload.client_id)
    state = (await db.execute(stmt)).scalar_one_or_none()
    
    if not state:
        state = RemediationKillSwitchState(
            client_id=payload.client_id,
            enabled=payload.enabled,
            reason=payload.reason,
            immutable_hash=compute_deterministic_hash(fields={"client_id": str(payload.client_id), "op": "kill_switch_init"})
        )
        db.add(state)
    else:
        state.enabled = payload.enabled
        state.reason = payload.reason
        state.immutable_hash = compute_deterministic_hash(fields={"client_id": str(payload.client_id), "enabled": state.enabled, "updated_at": str(state.updated_at)})
        
    await db.commit()
    await log_remediation_kill_switch_updated(db, payload.client_id, payload.enabled, payload.reason)
    await db.commit()
    
    return state

@router.get("/kill-switch")
async def get_remediation_kill_switch(
    client_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets the kill-switch state for a client."""
    stmt = select(RemediationKillSwitchState).where(RemediationKillSwitchState.client_id == client_id)
    state = (await db.execute(stmt)).scalar_one_or_none()
    if not state:
        return {"client_id": client_id, "enabled": False, "reason": "Not set"}
    return state

@router.get("/{execution_id}")
async def get_remediation_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets details of an execution."""
    stmt = select(RemediationExecution).where(RemediationExecution.id == execution_id)
    execution = (await db.execute(stmt)).scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution

@router.post("/{execution_id}/kill")
async def kill_remediation_execution(
    execution_id: uuid.UUID,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Emergency stop for an execution."""
    stmt = select(RemediationExecution).where(RemediationExecution.id == execution_id)
    execution = (await db.execute(stmt)).scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    await EXECUTOR.kill_execution(db, execution, reason)
    return {"status": "killed", "execution_id": execution_id}

@router.get("/{execution_id}/rollback-plan")
async def get_remediation_rollback_plan(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets the rollback plan for an execution."""
    stmt = select(RemediationRollbackPlan).where(RemediationRollbackPlan.execution_id == execution_id)
    rollback = (await db.execute(stmt)).scalar_one_or_none()
    if not rollback:
        raise HTTPException(status_code=404, detail="Rollback plan not found")
    return rollback
