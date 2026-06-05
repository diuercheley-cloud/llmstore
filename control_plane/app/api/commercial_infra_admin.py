# Owner: commercial-ops
import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from app.api.deps import get_admin_db, get_super_admin_db
from app.models.commercial_infra_simulation import (
    CommercialApprovalRecord,
    CommercialInfrastructureSimulation,
    CommercialSafetyPolicy,
)
from app.services.compliance.financial_controls import evaluate_control_policy
from app.services.routing.commercial_infra_execution import get_infra_execution_service
from app.services.routing.commercial_infra_simulation import (
    simulate_cluster_failover,
    simulate_reroute,
    simulate_scale_down,
    simulate_scale_up,
)
from app.services.routing.commercial_safety_gates import validate_simulation_against_policy
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/routing/infra", tags=["commercial-infra-simulation"])

@router.get("/adapters")
async def list_adapters():
    svc = get_infra_execution_service()
    return await svc.list_adapters()

@router.get("/local-gpu/metrics")
async def get_local_gpu_metrics():
    svc = get_infra_execution_service()
    adapter = svc.get_adapter("local_gpu")
    if not adapter:
        raise HTTPException(status_code=400, detail="Local GPU adapter not found")
    
    # settings is available on the adapter as self.settings
    if not adapter.settings.commercial_local_gpu_execution_enabled:
        return {"status": "disabled", "message": "Local GPU execution is disabled"}
        
    metrics = adapter.collect_gpu_metrics()
    return metrics

@router.get("/proxmox/capacity")
async def get_proxmox_capacity():
    svc = get_infra_execution_service()
    adapter = svc.get_adapter("proxmox")
    if not adapter:
        raise HTTPException(status_code=400, detail="Proxmox adapter not found")

    if not adapter.settings.commercial_proxmox_execution_enabled:
        return {"status": "disabled", "message": "Proxmox execution is disabled"}

    capacity = adapter.get_capacity()
    return capacity

@router.get("/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    limit: int = 50,
    db: AsyncSession = Depends(get_admin_db)
):
    from app.models.commercial_infra_simulation import CommercialExecutionRecord
    stmt = select(CommercialExecutionRecord).order_by(CommercialExecutionRecord.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    executions = result.scalars().all()
    return executions

@router.post("/simulations/{simulation_id}/execute")
async def execute_simulation(
    simulation_id: uuid.UUID,
    adapter: str = Body("mock"),
    dry_run: bool = Body(True),
    approval_id: Optional[uuid.UUID] = Body(None),
    confirm: bool = Body(False),
    actor: str = Body("admin"),
    db: AsyncSession = Depends(get_admin_db)
):
    svc = get_infra_execution_service()
    try:
        if not dry_run:
            sim = await db.get(CommercialInfrastructureSimulation, simulation_id)
            if sim is None:
                raise HTTPException(status_code=404, detail="Simulation not found")
            decision = await evaluate_control_policy(
                db,
                control_area="infra_execution",
                action_type="real_execution",
                target_type="CommercialInfrastructureSimulation",
                target_id=simulation_id,
                actor=actor,
                package_type="infra_execution",
                summary=f"Real infra execution for simulation {simulation_id}",
                before_state={"safety_gate_status": sim.safety_gate_status, "target_scope": sim.target_scope, "target_identifier": sim.target_identifier},
                after_state={"adapter": adapter, "dry_run": dry_run, "confirm": confirm},
                payload={"simulation_id": str(simulation_id), "adapter": adapter, "dry_run": dry_run, "confirm": confirm, "actor": actor},
                related_ids={"simulation_id": str(simulation_id)},
            )
            if decision.should_block and decision.approval_chain is not None:
                await db.commit()
                return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
        record = await svc.execute_simulation(
            db, 
            simulation_id=simulation_id,
            adapter_name=adapter,
            dry_run=dry_run,
            confirm=confirm,
            approval_id=approval_id
        )
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/executions/{execution_id}/rollback")
async def rollback_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_super_admin_db)
):
    svc = get_infra_execution_service()
    try:
        record = await svc.rollback_execution(db, execution_id)
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/executions/{execution_id}/status")
async def get_execution_status(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_admin_db)
):
    from app.models.commercial_infra_simulation import CommercialExecutionRecord
    record = await db.get(CommercialExecutionRecord, execution_id)
    if not record:
        raise HTTPException(status_code=404, detail="Execution record not found")
    
    if record.external_operation_id:
        svc = get_infra_execution_service()
        adapter = svc.get_adapter(record.adapter)
        if adapter:
            status = await adapter.get_status(record.external_operation_id)
            return {"record": record, "external_status": status}
            
    return {"record": record}

@router.get("/simulations", response_model=List[Dict[str, Any]])
async def list_simulations(
    limit: int = 50,
    db: AsyncSession = Depends(get_admin_db)
):
    stmt = select(CommercialInfrastructureSimulation).order_by(CommercialInfrastructureSimulation.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    simulations = result.scalars().all()
    return [
        {
            "id": s.id,
            "simulation_type": s.simulation_type,
            "target_scope": s.target_scope,
            "target_identifier": s.target_identifier,
            "requested_action": s.requested_action_json,
            "blast_radius": s.blast_radius,
            "safety_gate_status": s.safety_gate_status,
            "created_at": s.created_at,
            "predicted_impacts": {
                "cost": s.predicted_cost_impact_brl,
                "margin": s.predicted_margin_impact_brl,
                "sla": s.predicted_sla_impact_json
            }
        }
        for s in simulations
    ]

@router.post("/simulate")
async def create_simulation(
    simulation_type: str = Body(...),
    target_scope: str = Body(...),
    target_identifier: str = Body(...),
    requested_action: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_admin_db)
):
    if simulation_type == "scale_up":
        sim = await simulate_scale_up(db, target_scope, target_identifier, requested_action)
    elif simulation_type == "scale_down":
        sim = await simulate_scale_down(db, target_scope, target_identifier, requested_action)
    elif simulation_type == "reroute":
        sim = await simulate_reroute(db, target_scope, target_identifier, requested_action)
    elif simulation_type == "cluster_failover":
        sim = await simulate_cluster_failover(db, target_identifier, requested_action)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported simulation type: {simulation_type}")

    status, reason = await validate_simulation_against_policy(db, sim)
    sim.safety_gate_status = status
    await db.commit()
    
    return {
        "simulation_id": sim.id,
        "status": status,
        "reason": reason,
        "blast_radius": sim.blast_radius,
        "predicted_impacts": {
            "cost_brl": sim.predicted_cost_impact_brl,
            "margin_brl": sim.predicted_margin_impact_brl
        }
    }

@router.get("/safety-policies", response_model=List[Dict[str, Any]])
async def list_safety_policies(db: AsyncSession = Depends(get_admin_db)):
    stmt = select(CommercialSafetyPolicy)
    result = await db.execute(stmt)
    policies = result.scalars().all()
    return policies

@router.post("/safety-policies")
async def create_safety_policy(
    policy_name: str = Body(...),
    enabled: bool = Body(True),
    max_cost_increase: float = Body(20.0),
    max_margin_drop: float = Body(10.0),
    max_sla_violation: float = Body(5.0),
    db: AsyncSession = Depends(get_super_admin_db)
):
    policy = CommercialSafetyPolicy(
        id=uuid.uuid4(),
        policy_name=policy_name,
        enabled=enabled,
        max_predicted_cost_increase_percent=max_cost_increase,
        max_predicted_margin_drop_percent=max_margin_drop,
        max_predicted_sla_violation_percent=max_sla_violation
    )
    db.add(policy)
    await db.commit()
    return {"status": "created", "policy_id": policy.id}

@router.patch("/safety-policies/{policy_id}")
async def update_safety_policy(
    policy_id: uuid.UUID,
    updates: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_super_admin_db)
):
    stmt = update(CommercialSafetyPolicy).where(CommercialSafetyPolicy.id == policy_id).values(**updates)
    await db.execute(stmt)
    await db.commit()
    return {"status": "updated"}

@router.post("/validate")
async def validate_action(
    simulation_id: uuid.UUID = Body(...),
    db: AsyncSession = Depends(get_admin_db)
):
    stmt = select(CommercialInfrastructureSimulation).where(CommercialInfrastructureSimulation.id == simulation_id)
    result = await db.execute(stmt)
    sim = result.scalar_one_or_none()
    
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
        
    status, reason = await validate_simulation_against_policy(db, sim)
    sim.safety_gate_status = status
    await db.commit()
    
    return {"status": status, "reason": reason}

@router.get("/approvals", response_model=List[Dict[str, Any]])
async def list_approvals(db: AsyncSession = Depends(get_admin_db)):
    stmt = select(CommercialApprovalRecord).order_by(CommercialApprovalRecord.created_at.desc())
    result = await db.execute(stmt)
    approvals = result.scalars().all()
    return approvals

@router.post("/approvals")
async def create_approval(
    simulation_id: uuid.UUID = Body(...),
    status: str = Body(...), # approved|rejected
    notes: Optional[str] = Body(None),
    approver: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_super_admin_db)
):
    approval = CommercialApprovalRecord(
        id=uuid.uuid4(),
        simulation_id=simulation_id,
        status=status,
        notes=notes,
        approver=approver,
        created_at=datetime.now(UTC),
        decided_at=datetime.now(UTC)
    )
    db.add(approval)
    
    # Update simulation status if approved
    if status == "approved":
        await db.execute(
            update(CommercialInfrastructureSimulation)
            .where(CommercialInfrastructureSimulation.id == simulation_id)
            .values(safety_gate_status="allowed")
        )
        
    await db.commit()
    return {"status": "recorded", "approval_id": approval.id}
