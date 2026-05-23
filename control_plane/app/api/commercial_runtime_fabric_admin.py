# Owner: commercial-ops
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, require_admin_user
from app.services.runtime.runtime_fabric import RuntimeFabricService
from app.services.runtime.runtime_healing import RuntimeHealingService
from app.services.runtime.runtime_recovery import RuntimeRecoveryService
from app.services.runtime.determinism_repair import DeterminismRepairService
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter(prefix="/admin/runtime", tags=["Commercial Runtime Fabric Admin"])
portal_router = APIRouter(prefix="/portal/runtime", tags=["Customer Portal Runtime"])

# Schemas
class HeartbeatReport(BaseModel):
    node_id: str
    status: str
    metrics: Dict

class DriftReport(BaseModel):
    workflow_id: str
    step_index: int
    expected_hash: str
    actual_hash: str
    drift_details: Dict

class RecoveryPlanCreate(BaseModel):
    event_id: str
    mode: Optional[str] = "advisory"

# Admin Endpoints
@router.get("/fabric")
async def get_fabric_status(db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = RuntimeFabricService(db)
    return await service.get_fabric_health()

@router.post("/fabric/heartbeat")
async def report_heartbeat(report: HeartbeatReport, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = RuntimeFabricService(db)
    return await service.report_heartbeat(report.node_id, report.status, report.metrics)

@router.get("/healing")
async def list_healing_events(db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = RuntimeFabricService(db)
    return await service.get_recent_events()

@router.post("/recovery")
async def create_recovery_plan(plan_req: RecoveryPlanCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = RuntimeRecoveryService(db)
    return await service.create_recovery_plan(plan_req.event_id, plan_req.mode)

@router.post("/recovery/{plan_id}/execute")
async def execute_recovery_plan(plan_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = RuntimeRecoveryService(db)
    return await service.execute_plan(plan_id)

@router.get("/drift")
async def list_active_drifts(db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = DeterminismRepairService(db)
    return await service.get_active_drifts()

@router.post("/drift/report")
async def report_drift(report: DriftReport, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = DeterminismRepairService(db)
    return await service.report_drift(report.workflow_id, report.step_index, report.expected_hash, report.actual_hash, report.drift_details)

@router.post("/replay-repair/{drift_id}")
async def trigger_replay_repair(drift_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    drift_service = DeterminismRepairService(db)
    recovery_service = RuntimeRecoveryService(db)
    fabric_service = RuntimeFabricService(db)
    
    events = await fabric_service.get_recent_events(limit=10)
    event_id = None
    for e in events:
        if e.event_type == "drift_detected" and e.details.get("drift_id") == drift_id:
            event_id = e.id
            break
    
    if not event_id:
        raise HTTPException(status_code=404, detail="Drift event not found")
        
    plan = await recovery_service.create_recovery_plan(event_id, mode="guarded_recovery")
    return await recovery_service.execute_plan(plan.id)

# Portal Endpoints
@portal_router.get("/status")
async def get_runtime_status(db: AsyncSession = Depends(get_db)):
    service = RuntimeFabricService(db)
    health = await service.get_fabric_health()
    return {
        "status": "operational" if all(h.status == "healthy" for h in health) else "degraded",
        "nodes_online": len(health),
        "active_alerts": len([h for h in health if h.status != "healthy"])
    }
