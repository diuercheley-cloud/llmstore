# Owner: platform-ops
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.adapter_sandbox import (
    AdapterManifest,
    AdapterSandboxPolicyViolation,
    AdapterSandboxReceipt,
    AdapterSandboxRun,
    AdapterSandboxStepResult,
    compute_deterministic_hash,
)
from app.models.operations.remediation_execution import RemediationExecution
from app.services.operations.adapter_sandbox.audit_events import (
    log_adapter_manifest_blocked,
    log_adapter_policy_violation_detected,
    log_adapter_sandbox_run_completed,
    log_adapter_sandbox_run_prepared,
)
from app.services.operations.adapter_sandbox.manifest_validator import AdapterManifestValidator
from app.services.operations.adapter_sandbox.policy_guard import AdapterSandboxPolicyGuard
from app.services.operations.adapter_sandbox.receipts import (
    build_manifest_receipt,
    build_sandbox_run_receipt,
)
from app.services.operations.adapter_sandbox.sandbox_context import AdapterSandboxContext
from app.services.operations.adapter_sandbox.simulation_runner import AdapterSandboxSimulationRunner
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

VALIDATOR = AdapterManifestValidator()
GUARD = AdapterSandboxPolicyGuard()
RUNNER = AdapterSandboxSimulationRunner()

# --- Schemas ---

class AdapterManifestRegisterRequest(BaseModel):
    client_id: uuid.UUID
    adapter_name: str
    adapter_version: str
    adapter_type: str
    capabilities: List[str] = Field(default_factory=list)
    denied_capabilities: List[str] = Field(default_factory=list)

class SandboxRunPrepareRequest(BaseModel):
    client_id: uuid.UUID
    manifest_id: uuid.UUID
    execution_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None
    sandbox_mode: str = "simulation"

class SandboxRunSimulateRequest(BaseModel):
    client_id: uuid.UUID
    run_id: uuid.UUID
    steps: List[Dict[str, Any]]

# --- Endpoints ---

@router.post("/manifests")
async def register_adapter_manifest(
    payload: AdapterManifestRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Registers and validates an adapter manifest."""
    m_data = payload.model_dump()
    m_data["capabilities_json"] = {"allowed": payload.capabilities}
    m_data["denied_capabilities_json"] = {"denied": payload.denied_capabilities}
    
    # Defaults and mandates
    m_data["sandbox_required"] = True
    m_data["dry_run_default"] = True
    m_data["network_access_allowed"] = False
    m_data["subprocess_allowed"] = False
    m_data["external_system_access_allowed"] = False
    
    val_res = VALIDATOR.validate_manifest(m_data)
    
    manifest_hash = VALIDATOR.compute_manifest_hash(m_data)
    immutable_hash = compute_deterministic_hash(fields={**m_data, "client_id": str(payload.client_id)})
    
    manifest = AdapterManifest(
        client_id=payload.client_id,
        adapter_name=payload.adapter_name,
        adapter_version=payload.adapter_version,
        adapter_type=payload.adapter_type,
        capabilities_json=m_data["capabilities_json"],
        denied_capabilities_json=m_data["denied_capabilities_json"],
        sandbox_required=True,
        dry_run_default=True,
        network_access_allowed=False,
        subprocess_allowed=False,
        external_system_access_allowed=False,
        manifest_hash=manifest_hash,
        immutable_hash=immutable_hash
    )
    db.add(manifest)
    await db.flush()
    
    # Check for policy violations
    violations_data = VALIDATOR.detect_policy_violations(manifest)
    violations = []
    for v in violations_data:
        violation = AdapterSandboxPolicyViolation(
            client_id=payload.client_id,
            manifest_id=manifest.id,
            violation_type=v["violation_type"],
            severity=v["severity"],
            description=v["description"],
            blocked=v["blocked"],
            immutable_hash=compute_deterministic_hash(fields={**v, "manifest_id": str(manifest.id)})
        )
        db.add(violation)
        violations.append(violation)
        await log_adapter_policy_violation_detected(db, payload.client_id, violation.id, violation.violation_type)

    if GUARD.block_if_violation(violations_data) or not val_res["is_valid"]:
        await log_adapter_manifest_blocked(db, payload.client_id, manifest.id, "Policy or validation failure")
        await db.commit()
        return {"status": "blocked", "errors": val_res["errors"], "violations": violations}

    receipt_data = build_manifest_receipt(manifest)
    receipt = AdapterSandboxReceipt(
        client_id=payload.client_id,
        sandbox_run_id=None,
        receipt_type="manifest_registration",
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    await db.commit()
    
    return {"manifest": manifest, "violations": violations, "receipt": receipt}

@router.get("/manifests")
async def list_adapter_manifests(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Lists manifests for a client."""
    stmt = select(AdapterManifest).where(AdapterManifest.client_id == client_id).order_by(AdapterManifest.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/runs/prepare")
async def prepare_sandbox_run(
    payload: SandboxRunPrepareRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Prepares a sandbox run context."""
    stmt_m = select(AdapterManifest).where(AdapterManifest.id == payload.manifest_id)
    manifest = (await db.execute(stmt_m)).scalar_one_or_none()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
        
    run_data = RUNNER.prepare_run(manifest, payload.execution_id, payload.plan_id, payload.sandbox_mode)
    
    approval_verified = False
    gates_verified = False
    
    if payload.execution_id:
        stmt_e = select(RemediationExecution).where(RemediationExecution.id == payload.execution_id)
        execution = (await db.execute(stmt_e)).scalar_one_or_none()
        if execution:
            approval_verified = execution.approval_verified
            # In Phase 73, gates are verified if the execution reached a certain state or explicit flag
            gates_verified = getattr(execution, "gates_verified", False)

    immutable_hash = compute_deterministic_hash(fields={**run_data, "client_id": str(payload.client_id)})
    
    run = AdapterSandboxRun(
        client_id=payload.client_id,
        manifest_id=payload.manifest_id,
        execution_id=payload.execution_id,
        plan_id=payload.plan_id,
        sandbox_mode=payload.sandbox_mode,
        dry_run=True,
        approval_verified=approval_verified,
        gates_verified=gates_verified,
        status="pending",
        input_hash=run_data["input_hash"],
        immutable_hash=immutable_hash
    )
    db.add(run)
    await db.commit()
    await log_adapter_sandbox_run_prepared(db, payload.client_id, run.id)
    return run

@router.post("/runs/simulate")
async def simulate_sandbox_run(
    payload: SandboxRunSimulateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Simulates adapter execution."""
    stmt_run = select(AdapterSandboxRun).where(AdapterSandboxRun.id == payload.run_id)
    run = (await db.execute(stmt_run)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    stmt_m = select(AdapterManifest).where(AdapterManifest.id == run.manifest_id)
    manifest = (await db.execute(stmt_m)).scalar_one()
    
    context = AdapterSandboxContext(
        client_id=run.client_id,
        manifest_id=run.manifest_id,
        sandbox_mode=run.sandbox_mode,
        dry_run=run.dry_run,
        approval_verified=run.approval_verified,
        gates_verified=run.gates_verified,
        allowed_capabilities=manifest.capabilities_json.get("allowed", []),
        denied_capabilities=manifest.denied_capabilities_json.get("denied", []),
        approval_required=manifest.approval_required,
        gates_required=True # Mandatory for Phase 73
    )
    
    run.status = "simulated"
    run.started_at = datetime.now(timezone.utc)
    
    results = []
    for i, step in enumerate(payload.steps):
        res = RUNNER.simulate_step(context, step)
        step_res = AdapterSandboxStepResult(
            client_id=run.client_id,
            sandbox_run_id=run.id,
            step_order=i + 1,
            action_type=step.get("action_type", "unknown"),
            target_domain=step.get("target_domain", "unknown"),
            result_status=res["result_status"],
            simulated_output_json=res["simulated_output_json"],
            immutable_hash=compute_deterministic_hash(fields={"run_id": str(run.id), "order": i+1})
        )
        db.add(step_res)
        results.append(res)
        
    run.completed_at = datetime.now(timezone.utc)
    
    receipt_data = build_sandbox_run_receipt(run, results)
    receipt = AdapterSandboxReceipt(
        client_id=run.client_id,
        sandbox_run_id=run.id,
        receipt_type="sandbox_run",
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    
    await db.commit()
    await log_adapter_sandbox_run_completed(db, run.client_id, run.id, run.status)
    return {"run": run, "results": results, "receipt": receipt}

@router.get("/runs")
async def list_sandbox_runs(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Lists sandbox runs for a client."""
    stmt = select(AdapterSandboxRun).where(AdapterSandboxRun.client_id == client_id).order_by(AdapterSandboxRun.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/manifests/{manifest_id}")
async def get_adapter_manifest(
    manifest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets details of an adapter manifest."""
    stmt = select(AdapterManifest).where(AdapterManifest.id == manifest_id)
    manifest = (await db.execute(stmt)).scalar_one_or_none()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return manifest

@router.get("/runs/{run_id}")
async def get_sandbox_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets details of a sandbox run."""
    stmt = select(AdapterSandboxRun).where(AdapterSandboxRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/runs/{run_id}/receipt")
async def generate_sandbox_run_receipt(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Generates a receipt for a sandbox run."""
    stmt_run = select(AdapterSandboxRun).where(AdapterSandboxRun.id == run_id)
    run = (await db.execute(stmt_run)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    stmt_res = select(AdapterSandboxStepResult).where(AdapterSandboxStepResult.sandbox_run_id == run_id)
    results = (await db.execute(stmt_res)).scalars().all()
    
    results_list = [r.__dict__ for r in results]
    receipt_data = build_sandbox_run_receipt(run, results_list)
    
    receipt = AdapterSandboxReceipt(
        client_id=run.client_id,
        sandbox_run_id=run.id,
        receipt_type="sandbox_run",
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    await db.commit()
    return receipt

@router.get("/violations")
async def list_policy_violations(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Lists policy violations for a client."""
    stmt = select(AdapterSandboxPolicyViolation).where(AdapterSandboxPolicyViolation.client_id == client_id).order_by(AdapterSandboxPolicyViolation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
