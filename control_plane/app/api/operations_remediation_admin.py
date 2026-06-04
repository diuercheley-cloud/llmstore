# Owner: platform-ops
import uuid
from typing import Any, List

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.remediation_planning import (
    RemediationApprovalRequirement,
    RemediationPlan,
    RemediationPlanReceipt,
    RemediationStep,
    compute_deterministic_hash,
)
from app.services.operations.remediation.approval_requirements import (
    RemediationApprovalRequirementService,
)
from app.services.operations.remediation.audit_events import (
    log_remediation_approval_required,
    log_remediation_plan_proposed,
    log_remediation_plan_receipt_created,
    log_remediation_step_proposed,
)
from app.services.operations.remediation.blast_radius import RemediationBlastRadiusService
from app.services.operations.remediation.deterministic_planner import (
    DeterministicRemediationPlanner,
)
from app.services.operations.remediation.receipts import (
    build_remediation_plan_receipt,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

PLANNER = DeterministicRemediationPlanner()
BLAST_RADIUS_SERVICE = RemediationBlastRadiusService()
APPROVAL_SERVICE = RemediationApprovalRequirementService()

# --- Schemas ---

class RemediationPlanProposeRequest(BaseModel):
    client_id: uuid.UUID
    source_type: str = Field(..., description="Source of the remediation request (e.g., forecast, correlation)")
    source_ref: str = Field(..., description="Reference ID of the source")
    risk_level: str = Field("low", description="Initial risk level")
    involved_domains: List[str] = Field(default_factory=list, description="List of affected domains")
    dry_run: bool = True

# --- Endpoints ---

@router.post("/propose")
async def propose_remediation_plan(
    payload: RemediationPlanProposeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Generates a deterministic remediation plan. Advisory-only.
    """
    inputs = payload.model_dump()
    input_hash = PLANNER.compute_input_hash(inputs)
    
    # Check for existing plan with same input_hash
    stmt = select(RemediationPlan).where(
        RemediationPlan.client_id == payload.client_id,
        RemediationPlan.input_hash == input_hash
    )
    existing_plan = (await db.execute(stmt)).scalar_one_or_none()
    
    if existing_plan:
        return {"plan_id": existing_plan.id, "status": "existing", "immutable_hash": existing_plan.immutable_hash}

    # Build plan logic
    plan_data = PLANNER.build_plan(inputs, dry_run=payload.dry_run)
    steps_data = PLANNER.build_steps(plan_data, inputs)
    
    # Calculate blast radius explicitly
    plan_data["blast_radius"] = BLAST_RADIUS_SERVICE.calculate_blast_radius(inputs)
    
    # Determine immutable hash for the plan
    plan_immutable_hash = compute_deterministic_hash(fields={
        "client_id": str(payload.client_id),
        "plan_type": plan_data["plan_type"],
        "input_hash": input_hash,
        "blast_radius": plan_data["blast_radius"],
        "advisory_only": True
    })
    
    plan = RemediationPlan(
        client_id=payload.client_id,
        plan_type=plan_data["plan_type"],
        source_type=plan_data["source_type"],
        source_ref=plan_data["source_ref"],
        risk_level=plan_data["risk_level"],
        blast_radius=plan_data["blast_radius"],
        requires_approval=plan_data["requires_approval"],
        advisory_only=True,
        dry_run=plan_data["dry_run"],
        input_hash=input_hash,
        immutable_hash=plan_immutable_hash,
        status="proposed"
    )
    db.add(plan)
    await db.flush() # Get plan.id
    
    # Create steps
    steps = []
    for step_data in steps_data:
        step_immutable_hash = compute_deterministic_hash(fields={
            "plan_id": str(plan.id),
            "step_order": step_data["step_order"],
            "action_type": step_data["action_type"],
            "target_domain": step_data["target_domain"]
        })
        step = RemediationStep(
            client_id=payload.client_id,
            plan_id=plan.id,
            step_order=step_data["step_order"],
            action_type=step_data["action_type"],
            target_domain=step_data["target_domain"],
            target_ref=step_data["target_ref"],
            description=step_data["description"],
            expected_effect=step_data["expected_effect"],
            reversible=step_data["reversible"],
            requires_approval=step_data["requires_approval"],
            advisory_only=True,
            dry_run=step_data["dry_run"],
            immutable_hash=step_immutable_hash
        )
        db.add(step)
        steps.append(step)
        
    # Determine approval requirements
    approval_reqs_data = APPROVAL_SERVICE.determine_required_approvals(plan_data, steps_data)
    approval_requirements = []
    for req_data in approval_reqs_data:
        req_immutable_hash = compute_deterministic_hash(fields={
            "plan_id": str(plan.id),
            "approval_scope": req_data["approval_scope"],
            "required_role": req_data["required_role"]
        })
        req = RemediationApprovalRequirement(
            client_id=payload.client_id,
            plan_id=plan.id,
            approval_scope=req_data["approval_scope"],
            required_role=req_data["required_role"],
            reason=req_data["reason"],
            immutable_hash=req_immutable_hash
        )
        db.add(req)
        approval_requirements.append(req)
        
    await db.commit()
    
    # Log events
    await log_remediation_plan_proposed(db, payload.client_id, plan.id, plan.plan_type)
    for step in steps:
        await log_remediation_step_proposed(db, payload.client_id, step.id, step.action_type)
    for req in approval_requirements:
        await log_remediation_approval_required(db, payload.client_id, plan.id, req.approval_scope)
    await db.commit()
    
    explanation = PLANNER.explain_plan(plan_data, steps_data)
    
    return {
        "plan": plan,
        "steps": steps,
        "approval_requirements": approval_requirements,
        "explanation": explanation
    }

@router.get("/")
async def list_remediation_plans(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Lists all remediation plans for a client."""
    stmt = select(RemediationPlan).where(RemediationPlan.client_id == client_id).order_by(RemediationPlan.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{plan_id}")
async def get_remediation_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets details of a remediation plan."""
    stmt = select(RemediationPlan).where(RemediationPlan.id == plan_id)
    plan = (await db.execute(stmt)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.get("/{plan_id}/steps")
async def get_remediation_steps(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets steps of a remediation plan."""
    stmt = select(RemediationStep).where(RemediationStep.plan_id == plan_id).order_by(RemediationStep.step_order.asc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{plan_id}/approvals")
async def get_remediation_approvals(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Gets approval requirements of a remediation plan."""
    stmt = select(RemediationApprovalRequirement).where(RemediationApprovalRequirement.plan_id == plan_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{plan_id}/receipt")
async def generate_remediation_receipt(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """Generates a receipt for a remediation plan."""
    stmt = select(RemediationPlan).where(RemediationPlan.id == plan_id)
    plan = (await db.execute(stmt)).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    stmt_steps = select(RemediationStep).where(RemediationStep.plan_id == plan_id).order_by(RemediationStep.step_order.asc())
    steps = (await db.execute(stmt_steps)).scalars().all()
    
    plan_dict = {
        "id": str(plan.id),
        "client_id": str(plan.client_id),
        "plan_type": plan.plan_type,
        "risk_level": plan.risk_level,
        "blast_radius": plan.blast_radius,
        "deterministic_version": plan.deterministic_version,
        "dry_run": plan.dry_run
    }
    steps_list = [
        {"step_order": s.step_order, "action_type": s.action_type, "target_domain": s.target_domain}
        for s in steps
    ]
    
    receipt_data = build_remediation_plan_receipt(plan_dict, steps_list)
    
    receipt = RemediationPlanReceipt(
        client_id=plan.client_id,
        plan_id=plan.id,
        receipt_type=receipt_data["receipt_type"],
        payload_hash=receipt_data["payload_hash"],
        immutable_hash=receipt_data["immutable_hash"],
        signature=receipt_data["signature"]
    )
    db.add(receipt)
    await db.commit()
    
    await log_remediation_plan_receipt_created(db, plan.client_id, receipt.id, plan.id)
    await db.commit()
    
    return receipt
