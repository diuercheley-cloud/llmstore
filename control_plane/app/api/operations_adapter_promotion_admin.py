# Owner: platform-ops
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.adapter_promotion import (
    AdapterPromotionWorkflow,
    AdapterPromotionGateResult,
    AdapterPromotionStageTransition,
    AdapterPromotionRollback,
    AdapterPromotionReceipt,
)
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_promotion.workflow_service import AdapterPromotionWorkflowService
from app.services.operations.adapter_promotion.gates import AdapterPromotionGateService
from app.services.operations.adapter_promotion.staging_simulation import AdapterStagingSimulationService
from app.services.operations.adapter_promotion.receipts import (
    build_promotion_workflow_receipt,
    build_gate_result_receipt,
    build_transition_receipt,
    build_rollback_receipt,
)

router = APIRouter()

GATE_SERVICE = AdapterPromotionGateService()
STAGING_SERVICE = AdapterStagingSimulationService()

# --- Schemas ---

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    registry_entry_id: uuid.UUID
    adapter_name: str
    adapter_version: str
    current_stage: str
    target_stage: str
    promotion_status: str
    immutable_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

class WorkflowCreateRequest(BaseModel):
    client_id: uuid.UUID
    registry_entry_id: uuid.UUID
    target_stage: str
    context: Optional[Dict[str, Any]] = {}

class GateResultResponse(BaseModel):
    id: uuid.UUID
    gate_name: str
    gate_status: str
    reason: Optional[str]
    required: bool
    blocking: bool

    class Config:
        from_attributes = True

class TransitionResponse(BaseModel):
    id: uuid.UUID
    from_stage: str
    to_stage: str
    transition_status: str
    reason: Optional[str]

    class Config:
        from_attributes = True

class RollbackResponse(BaseModel):
    id: uuid.UUID
    from_stage: str
    rollback_to_stage: str
    reason: str
    rollback_status: str

    class Config:
        from_attributes = True

class PromotionResultResponse(BaseModel):
    workflow: WorkflowResponse
    gate_results: List[GateResultResponse]
    receipt_id: Optional[str]

# --- Endpoints ---

@router.post("/workflows", response_model=PromotionResultResponse)
async def create_promotion_workflow(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    # Fetch registry entry
    stmt = select(SignedAdapterRegistryEntry).where(
        SignedAdapterRegistryEntry.id == request.registry_entry_id,
        SignedAdapterRegistryEntry.client_id == request.client_id
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")

    # Fetch manifest
    stmt = select(AdapterManifest).where(AdapterManifest.id == entry.manifest_id)
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()

    workflow_service = AdapterPromotionWorkflowService(db)
    workflow = await workflow_service.create_workflow(entry, request.target_stage)
    
    # Evaluate gates
    gate_results_raw = GATE_SERVICE.evaluate_gates(entry, request.target_stage, manifest, request.context)
    gate_results = await workflow_service.record_gate_results(workflow, gate_results_raw)
    
    receipt = build_promotion_workflow_receipt(workflow)
    db.add(receipt)
    
    await db.commit()
    await db.refresh(workflow)
    
    return PromotionResultResponse(
        workflow=WorkflowResponse.from_orm(workflow),
        gate_results=[GateResultResponse.from_orm(gr) for gr in gate_results],
        receipt_id=str(receipt.id)
    )

@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_promotion_workflows(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionWorkflow).where(AdapterPromotionWorkflow.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_promotion_workflow(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionWorkflow).where(
        AdapterPromotionWorkflow.id == workflow_id,
        AdapterPromotionWorkflow.client_id == client_id
    )
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Promotion workflow not found")
    return wf

@router.post("/workflows/{workflow_id}/promote")
async def promote_adapter(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionWorkflow).where(
        AdapterPromotionWorkflow.id == workflow_id,
        AdapterPromotionWorkflow.client_id == client_id
    )
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Promotion workflow not found")
    
    if wf.promotion_status == "blocked":
        raise HTTPException(status_code=400, detail="Workflow is blocked by gates")
    
    workflow_service = AdapterPromotionWorkflowService(db)
    transition = await workflow_service.propose_transition(wf, wf.target_stage)
    
    try:
        await workflow_service.promote(wf, transition)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    receipt = build_transition_receipt(transition)
    db.add(receipt)
    
    await db.commit()
    return {"transition": TransitionResponse.from_orm(transition), "workflow": WorkflowResponse.from_orm(wf), "receipt_id": str(receipt.id)}

@router.post("/workflows/{workflow_id}/rollback")
async def rollback_promotion(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    rollback_to_stage: str,
    reason: str = Query(..., min_length=5),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionWorkflow).where(
        AdapterPromotionWorkflow.id == workflow_id,
        AdapterPromotionWorkflow.client_id == client_id
    )
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Promotion workflow not found")
    
    workflow_service = AdapterPromotionWorkflowService(db)
    try:
        rollback = await workflow_service.rollback(wf, rollback_to_stage, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    receipt = build_rollback_receipt(rollback)
    db.add(receipt)
    
    await db.commit()
    return {"rollback": RollbackResponse.from_orm(rollback), "workflow": WorkflowResponse.from_orm(wf), "receipt_id": str(receipt.id)}

@router.get("/workflows/{workflow_id}/gates", response_model=List[GateResultResponse])
async def list_gate_results(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionGateResult).where(
        AdapterPromotionGateResult.workflow_id == workflow_id,
        AdapterPromotionGateResult.client_id == client_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/workflows/{workflow_id}/transitions", response_model=List[TransitionResponse])
async def list_transitions(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionStageTransition).where(
        AdapterPromotionStageTransition.workflow_id == workflow_id,
        AdapterPromotionStageTransition.client_id == client_id
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/workflows/{workflow_id}/receipt")
async def generate_promotion_receipt(
    workflow_id: uuid.UUID,
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin)
):
    stmt = select(AdapterPromotionWorkflow).where(
        AdapterPromotionWorkflow.id == workflow_id,
        AdapterPromotionWorkflow.client_id == client_id
    )
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Promotion workflow not found")
    
    receipt = build_promotion_workflow_receipt(wf)
    db.add(receipt)
    await db.commit()
    return receipt
