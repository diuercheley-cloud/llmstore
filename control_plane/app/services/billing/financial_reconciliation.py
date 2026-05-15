import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.models.commercial_queue_chargeback import CommercialQueueChargeback
from app.models.ai_wallet import AiWalletTransaction
from app.models.billing_invoice import BillingInvoice
from app.models.commercial_financial_reconciliation import CommercialFinancialReconciliation
from app.services.billing.financial_audit_trail import FinancialAuditTrailService
from app.services.notifications.revenue_escalations import evaluate_escalation_policies


class FinancialReconciliationService:
    @staticmethod
    async def reconcile_qos_billing(db: AsyncSession, period_start: datetime, period_end: datetime) -> List[CommercialFinancialReconciliation]:
        """
        Reconciles CommercialQoSBillingRecord with CommercialQueueChargeback.
        """
        settings = get_settings()
        
        # Get all billing records for the period
        stmt = select(CommercialQoSBillingRecord).where(
            and_(
                CommercialQoSBillingRecord.created_at >= period_start,
                CommercialQoSBillingRecord.created_at <= period_end
            )
        )
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        reconciliations = []
        
        for record in records:
            if not record.chargeback_id:
                continue
                
            # Get the original chargeback
            stmt_cb = select(CommercialQueueChargeback).where(CommercialQueueChargeback.id == record.chargeback_id)
            cb = (await db.execute(stmt_cb)).scalar_one_or_none()
            
            if not cb:
                # Discrepancy: Record exists but chargeback is missing
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="qos_billing",
                    client_id=record.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=record.billable_amount_brl,
                    actual_amount=Decimal("0.000000"),
                    status="mismatch",
                    notes=f"QoS Billing Record {record.id} references missing chargeback {record.chargeback_id}"
                )
                reconciliations.append(recon)
                continue
            
            # Recalculate expected amount from chargeback
            expected_amount = Decimal(str(cb.estimated_internal_cost_brl))
            if settings.commercial_qos_billing_include_opportunity_cost:
                expected_amount += Decimal(str(cb.estimated_opportunity_cost_brl))
            
            actual_amount = record.billable_amount_brl
            
            delta = actual_amount - expected_amount
            discrepancy_percent = (abs(delta) / expected_amount * 100) if expected_amount > 0 else 0
            
            status = "matched"
            if abs(discrepancy_percent) > settings.commercial_financial_reconciliation_threshold_percent:
                status = "mismatch"
            elif abs(discrepancy_percent) > 0:
                status = "warning"
                
            if status != "matched":
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="qos_billing",
                    client_id=record.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=expected_amount,
                    actual_amount=actual_amount,
                    status=status,
                    notes=f"Discrepancy in QoS Billing Record {record.id}. Delta: {delta} ({discrepancy_percent}%)",
                    metadata_json={"record_id": str(record.id), "chargeback_id": str(cb.id)}
                )
                reconciliations.append(recon)
                
                if status == "mismatch":
                    await FinancialAuditTrailService.create_audit_event(
                        db,
                        event_type="reconciliation_mismatch",
                        client_id=record.client_id,
                        related_record_type="CommercialQoSBillingRecord",
                        related_record_id=str(record.id),
                        amount_brl=delta,
                        metadata_json={"expected": str(expected_amount), "actual": str(actual_amount)}
                    )
        
        await db.commit()
        return reconciliations

    @staticmethod
    async def reconcile_wallet_debits(db: AsyncSession, period_start: datetime, period_end: datetime) -> List[CommercialFinancialReconciliation]:
        """
        Reconciles AiWalletTransaction with CommercialQoSBillingRecord.
        """
        # Select QoS billing records that should have been debited
        stmt = select(CommercialQoSBillingRecord).where(
            and_(
                CommercialQoSBillingRecord.status == "debited",
                CommercialQoSBillingRecord.processed_at >= period_start,
                CommercialQoSBillingRecord.processed_at <= period_end
            )
        )
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        reconciliations = []
        
        for record in records:
            if not record.wallet_transaction_id:
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="wallet",
                    client_id=record.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=record.billable_amount_brl,
                    actual_amount=Decimal("0.000000"),
                    status="mismatch",
                    notes=f"QoS Billing Record {record.id} status is 'debited' but wallet_transaction_id is null"
                )
                reconciliations.append(recon)
                continue
                
            stmt_tx = select(AiWalletTransaction).where(AiWalletTransaction.id == record.wallet_transaction_id)
            tx = (await db.execute(stmt_tx)).scalar_one_or_none()
            
            if not tx:
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="wallet",
                    client_id=record.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=record.billable_amount_brl,
                    actual_amount=Decimal("0.000000"),
                    status="mismatch",
                    notes=f"QoS Billing Record {record.id} references missing wallet transaction {record.wallet_transaction_id}"
                )
                reconciliations.append(recon)
                continue
            
            # Wallet amounts are usually stored as positive for credit, negative for debit?
            # Looking at ai_wallet.py, it doesn't specify. 
            # qos_billing.py uses wallet_service.debit_usage which likely creates a negative or absolute amount.
            # Assuming amount_brl in transaction matches billable_amount_brl (likely absolute or negated)
            
            actual_amount = abs(tx.amount_brl)
            expected_amount = record.billable_amount_brl
            
            if actual_amount != expected_amount:
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="wallet",
                    client_id=record.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=expected_amount,
                    actual_amount=actual_amount,
                    status="mismatch",
                    notes=f"Wallet transaction amount mismatch for Record {record.id}. Expected {expected_amount}, got {actual_amount}",
                    metadata_json={"record_id": str(record.id), "tx_id": str(tx.id)}
                )
                reconciliations.append(recon)
        
        await db.commit()
        return reconciliations

    @staticmethod
    async def reconcile_invoice_totals(db: AsyncSession, period_start: datetime, period_end: datetime) -> List[CommercialFinancialReconciliation]:
        """
        Reconciles BillingInvoice with associated CommercialQoSBillingRecord.
        """
        # Sum billable_amount_brl for each invoice
        stmt = select(
            CommercialQoSBillingRecord.invoice_id,
            func.sum(CommercialQoSBillingRecord.billable_amount_brl).label("total_billable")
        ).where(
            and_(
                CommercialQoSBillingRecord.invoice_id.isnot(None),
                CommercialQoSBillingRecord.processed_at >= period_start,
                CommercialQoSBillingRecord.processed_at <= period_end
            )
        ).group_by(CommercialQoSBillingRecord.invoice_id)
        
        result = await db.execute(stmt)
        invoice_summaries = result.all()
        
        reconciliations = []
        
        for inv_id, total_billable in invoice_summaries:
            stmt_inv = select(BillingInvoice).where(BillingInvoice.id == inv_id)
            invoice = (await db.execute(stmt_inv)).scalar_one_or_none()
            
            if not invoice:
                continue
            
            # This is tricky because invoice.total_amount includes base price + overage + QoS items
            # We need to know how much of the invoice total is supposedly from QoS
            # For simplicity, we assume we can track it or just check if invoice total is at least total_billable
            
            if invoice.total_amount < total_billable:
                recon = await FinancialReconciliationService._create_reconciliation_record(
                    db,
                    reconciliation_type="invoice",
                    client_id=invoice.client_id,
                    period_start=period_start,
                    period_end=period_end,
                    expected_amount=total_billable,
                    actual_amount=invoice.total_amount,
                    status="mismatch",
                    notes=f"Invoice {invoice.id} total {invoice.total_amount} is less than summed QoS billable amount {total_billable}",
                    metadata_json={"invoice_id": str(invoice.id)}
                )
                reconciliations.append(recon)
        
        await db.commit()
        return reconciliations

    @staticmethod
    async def _create_reconciliation_record(
        db: AsyncSession,
        reconciliation_type: str,
        client_id: Optional[uuid.UUID],
        period_start: datetime,
        period_end: datetime,
        expected_amount: Decimal,
        actual_amount: Decimal,
        status: str,
        notes: str,
        metadata_json: Optional[dict] = None
    ) -> CommercialFinancialReconciliation:
        delta = actual_amount - expected_amount
        discrepancy_percent = (abs(delta) / expected_amount * 100) if expected_amount > 0 else 0
        
        recon = CommercialFinancialReconciliation(
            reconciliation_type=reconciliation_type,
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
            expected_amount_brl=expected_amount,
            actual_amount_brl=actual_amount,
            delta_amount_brl=delta,
            discrepancy_percent=discrepancy_percent,
            status=status,
            notes=notes,
            metadata_json=metadata_json
        )
        db.add(recon)
        await db.flush()
        if status == "mismatch":
            recent_stmt = select(func.count(CommercialFinancialReconciliation.id)).where(
                CommercialFinancialReconciliation.status == "mismatch",
                CommercialFinancialReconciliation.reconciliation_type == reconciliation_type,
                CommercialFinancialReconciliation.created_at >= utc_now() - timedelta(hours=24),
            )
            if client_id is not None:
                recent_stmt = recent_stmt.where(CommercialFinancialReconciliation.client_id == client_id)
            recent_count = (await db.execute(recent_stmt)).scalar() or 0
            if recent_count >= 3:
                await evaluate_escalation_policies(
                    db,
                    source_type="reconciliation",
                    source_id=recon.id,
                    severity="critical" if discrepancy_percent >= 10 else "high",
                    summary=notes,
                    recommendation="Investigate repeated reconciliation mismatches and ledger drift.",
                    metadata=metadata_json or {},
                    trigger_type="repeated_mismatches",
                )
        return recon

    @staticmethod
    async def detect_financial_discrepancies(db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """
        Runs all reconciliation tasks for the specified lookback period.
        """
        period_end = utc_now()
        period_start = period_end - timedelta(hours=hours)
        
        qos_recons = await FinancialReconciliationService.reconcile_qos_billing(db, period_start, period_end)
        wallet_recons = await FinancialReconciliationService.reconcile_wallet_debits(db, period_start, period_end)
        invoice_recons = await FinancialReconciliationService.reconcile_invoice_totals(db, period_start, period_end)
        
        return {
            "period_start": period_start,
            "period_end": period_end,
            "qos_billing_discrepancies": len(qos_recons),
            "wallet_discrepancies": len(wallet_recons),
            "invoice_discrepancies": len(invoice_recons),
            "total_discrepancies": len(qos_recons) + len(wallet_recons) + len(invoice_recons)
        }

    @staticmethod
    async def summarize_reconciliation(db: AsyncSession) -> Dict[str, Any]:
        """
        Summarizes all reconciliation records.
        """
        stmt = select(
            CommercialFinancialReconciliation.status,
            func.count(CommercialFinancialReconciliation.id),
            func.sum(func.abs(CommercialFinancialReconciliation.delta_amount_brl))
        ).group_by(CommercialFinancialReconciliation.status)
        
        result = await db.execute(stmt)
        summary = result.all()
        
        return {
            str(status): {"count": count, "total_delta": float(total_delta or 0)}
            for status, count, total_delta in summary
        }

    @staticmethod
    async def mark_reconciliation_resolved(db: AsyncSession, recon_id: uuid.UUID, notes: str) -> bool:
        """
        Marks a reconciliation record as resolved.
        """
        stmt = select(CommercialFinancialReconciliation).where(CommercialFinancialReconciliation.id == recon_id)
        recon = (await db.execute(stmt)).scalar_one_or_none()
        
        if not recon:
            return False
            
        recon.status = "resolved"
        recon.notes = (recon.notes or "") + f"\n\nResolution Notes: {notes}"
        recon.resolved_at = utc_now()
        
        await db.commit()
        return True
