# Owner: commercial-ops
import uuid
from datetime import timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_admin_token
from app.services.billing.qos_billing import CommercialQoSBillingService
from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.services.compliance.financial_controls import evaluate_control_policy

router = APIRouter()

@router.get("/overview")
async def get_qos_billing_overview(
    hours: int = Query(24, ge=1, le=8760),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Returns an overview of QoS billing records and totals.
    """
    return await CommercialQoSBillingService.summarize_qos_billing(db, hours)

@router.post("/generate")
async def generate_qos_billing_records(
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Manually triggers generation of billing records from chargeback data.
    """
    records = await CommercialQoSBillingService.generate_qos_billing_records(db, hours)
    return {"calculated_count": len(records)}

@router.post("/{record_id}/attach-invoice")
async def attach_to_invoice(
    record_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Attaches a specific billing record to an invoice.
    """
    stmt = select(CommercialQoSBillingRecord).where(CommercialQoSBillingRecord.id == record_id)
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Billing record not found")
        
    success = await CommercialQoSBillingService.attach_to_invoice(db, record, invoice_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to attach to invoice. Check record status and mode.")
    
    await db.commit()
    return {"status": "success", "record_status": record.status}

@router.post("/{record_id}/debit-wallet")
async def debit_wallet(
    record_id: uuid.UUID,
    actor: str = Query(default="admin"),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Manually triggers wallet debit for a specific billing record.
    """
    stmt = select(CommercialQoSBillingRecord).where(CommercialQoSBillingRecord.id == record_id)
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Billing record not found")
    decision = await evaluate_control_policy(
        db,
        control_area="wallet",
        action_type="qos_manual_debit",
        target_type="CommercialQoSBillingRecord",
        target_id=record_id,
        actor=actor,
        package_type="wallet_debit",
        summary=f"Manual QoS wallet debit for record {record_id}",
        before_state={"status": record.status, "wallet_transaction_id": str(record.wallet_transaction_id) if record.wallet_transaction_id else None},
        after_state={"status": "debited", "amount_brl": str(record.billable_amount_brl)},
        payload={"actor": actor, "record_id": str(record_id)},
        related_ids={"record_id": str(record_id), "client_id": str(record.client_id)},
    )
    if decision.should_block and decision.approval_chain is not None:
        await db.commit()
        return {"status": "pending_approval", "approval_chain_id": str(decision.approval_chain.id)}
        
    tx = await CommercialQoSBillingService.debit_wallet_for_qos(db, record)
    if not tx:
        raise HTTPException(status_code=400, detail=f"Failed to debit wallet: {record.error_message}")
    
    await db.commit()
    return {"status": "success", "transaction_id": str(tx.id)}

@router.get("/records")
async def list_qos_billing_records(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Lists recent QoS billing records.
    """
    stmt = select(CommercialQoSBillingRecord).order_by(CommercialQoSBillingRecord.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/export")
async def export_qos_billing_records(
    format: str = Query("json", pattern="^(json|csv)$"),
    hours: int = Query(24, ge=1, le=8760),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(get_admin_token)
):
    """
    Exports QoS billing records in JSON or CSV format.
    """
    from fastapi.responses import JSONResponse, Response
    import csv
    import io

    stmt = select(CommercialQoSBillingRecord).where(CommercialQoSBillingRecord.created_at >= utc_now() - timedelta(hours=hours))
    result = await db.execute(stmt)
    records = result.scalars().all()

    if format == "json":
        return records
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "client_id", "qos_tier", "model", "period_start", "period_end",
            "billable_amount_brl", "status", "processed_at", "error_message"
        ])
        for r in records:
            writer.writerow([
                str(r.id), str(r.client_id), r.qos_tier, r.model or "",
                r.period_start.isoformat(), r.period_end.isoformat(),
                float(r.billable_amount_brl), r.status,
                r.processed_at.isoformat() if r.processed_at else "",
                r.error_message or ""
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=qos_billing_{hours}h.csv"}
        )
