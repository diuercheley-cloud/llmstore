import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.billing.financial_reconciliation import FinancialReconciliationService
from app.services.billing.dispute_management import DisputeManagementService
from app.services.billing.financial_audit_trail import FinancialAuditTrailService
from app.models.commercial_financial_reconciliation import CommercialFinancialReconciliation
from app.models.commercial_billing_dispute import CommercialBillingDispute
from app.services.compliance.financial_controls import evaluate_control_policy


router = APIRouter(
    prefix="/admin/billing",
    tags=["admin", "billing", "reconciliation"],
    dependencies=[Depends(require_admin)],
)


class ReconciliationRunRequest(BaseModel):
    hours: int = 24


class DisputeReviewRequest(BaseModel):
    admin_notes: str


class DisputeResolutionRequest(BaseModel):
    resolution_notes: str
    credit_amount_brl: Decimal = Decimal("0.000000")
    admin_id: str = "admin"


class ManualCreditRequest(BaseModel):
    client_id: uuid.UUID
    amount_brl: Decimal
    reason: str
    admin_id: str


# --- Reconciliation Endpoints ---

@router.get("/reconciliation/overview")
async def get_reconciliation_overview(db: AsyncSession = Depends(get_db_session)):
    return await FinancialReconciliationService.summarize_reconciliation(db)


@router.post("/reconciliation/run")
async def run_reconciliation(
    request: ReconciliationRunRequest,
    db: AsyncSession = Depends(get_db_session)
):
    return await FinancialReconciliationService.detect_financial_discrepancies(db, hours=request.hours)


@router.get("/reconciliation/mismatches")
async def get_reconciliation_mismatches(
    status: Optional[str] = "mismatch",
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialFinancialReconciliation).where(
        CommercialFinancialReconciliation.status == status
    ).order_by(desc(CommercialFinancialReconciliation.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


# --- Dispute Endpoints ---

@router.get("/disputes")
async def get_disputes(
    status: Optional[str] = None,
    client_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialBillingDispute)
    if status:
        stmt = stmt.where(CommercialBillingDispute.status == status)
    if client_id:
        stmt = stmt.where(CommercialBillingDispute.client_id == client_id)
        
    stmt = stmt.order_by(desc(CommercialBillingDispute.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/disputes/{id}/review")
async def review_dispute(
    id: uuid.UUID,
    request: DisputeReviewRequest,
    db: AsyncSession = Depends(get_db_session)
):
    success = await DisputeManagementService.review_dispute(db, id, request.admin_notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not mark dispute as under review")
    return {"status": "success"}


@router.post("/disputes/{id}/resolve")
async def resolve_dispute(
    id: uuid.UUID,
    request: DisputeResolutionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    dispute = await db.get(CommercialBillingDispute, id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if request.credit_amount_brl > 0:
        decision = await evaluate_control_policy(
            db,
            control_area="disputes",
            action_type="dispute_credit",
            target_type="CommercialBillingDispute",
            target_id=id,
            actor=request.admin_id,
            package_type="dispute_resolution",
            summary=f"Dispute credit resolution for {id}",
            before_state={"status": dispute.status, "credit_transaction_id": str(dispute.credit_transaction_id) if dispute.credit_transaction_id else None},
            after_state={"status": "credited", "credit_amount_brl": str(request.credit_amount_brl)},
            payload=request.model_dump(mode="json"),
            related_ids={"dispute_id": str(id), "client_id": str(dispute.client_id)},
        )
        if decision.should_block and decision.approval_chain is not None:
            await db.commit()
            return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
    success = await DisputeManagementService.resolve_dispute(
        db, id, request.resolution_notes, request.credit_amount_brl
    )
    if not success:
        raise HTTPException(status_code=400, detail="Could not resolve dispute")
    return {"status": "success"}


@router.post("/disputes/{id}/reject")
async def reject_dispute(
    id: uuid.UUID,
    request: DisputeResolutionRequest, # Reuse schema
    db: AsyncSession = Depends(get_db_session)
):
    success = await DisputeManagementService.reject_dispute(db, id, request.resolution_notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not reject dispute")
    return {"status": "success"}


@router.post("/disputes/manual-credit")
async def create_manual_credit(
    request: ManualCreditRequest,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        decision = await evaluate_control_policy(
            db,
            control_area="billing",
            action_type="manual_credit",
            target_type="Client",
            target_id=request.client_id,
            actor=request.admin_id,
            package_type="manual_credit",
            summary=f"Manual wallet credit for client {request.client_id}",
            before_state={"client_id": str(request.client_id)},
            after_state={"amount_brl": str(request.amount_brl), "reason": request.reason},
            payload=request.model_dump(mode="json"),
            related_ids={"client_id": str(request.client_id)},
        )
        if decision.should_block and decision.approval_chain is not None:
            await db.commit()
            return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
        tx = await DisputeManagementService.create_manual_credit(
            db, request.client_id, request.amount_brl, request.reason, request.admin_id
        )
        return {"status": "success", "transaction_id": str(tx.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ReconciliationResolveRequest(BaseModel):
    notes: str
    admin_id: str = "admin"


@router.post("/reconciliation/{id}/resolve")
async def resolve_reconciliation(
    id: uuid.UUID,
    request: ReconciliationResolveRequest,
    db: AsyncSession = Depends(get_db_session),
):
    recon = await db.get(CommercialFinancialReconciliation, id)
    if recon is None:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    decision = await evaluate_control_policy(
        db,
        control_area="reconciliation",
        action_type="resolve_mismatch",
        target_type="CommercialFinancialReconciliation",
        target_id=id,
        actor=request.admin_id,
        package_type="reconciliation_mismatch",
        summary=f"Resolve reconciliation mismatch {id}",
        before_state={"status": recon.status, "notes": recon.notes},
        after_state={"status": "resolved", "notes": request.notes},
        payload=request.model_dump(mode="json"),
        related_ids={"reconciliation_id": str(id), "client_id": str(recon.client_id) if recon.client_id else None},
    )
    if decision.should_block and decision.approval_chain is not None:
        await db.commit()
        return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
    success = await FinancialReconciliationService.mark_reconciliation_resolved(db, id, request.notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not resolve reconciliation")
    return {"status": "success"}


# --- Audit Endpoints ---

@router.get("/audit/validate-chain")
async def validate_audit_chain(db: AsyncSession = Depends(get_db_session)):
    valid = await FinancialAuditTrailService.validate_audit_chain(db)
    return {"is_valid": valid}
