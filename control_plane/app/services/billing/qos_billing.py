import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.ai_wallet import AiWalletTransaction
from app.models.billing_invoice import BillingInvoice
from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.models.commercial_queue_chargeback import CommercialQueueChargeback
from app.services.billing import wallet_service
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class CommercialQoSBillingService:
    @staticmethod
    async def calculate_qos_billable_amount(chargeback: CommercialQueueChargeback) -> Decimal:
        """
        Calculates the billable amount based on internal cost and optionally opportunity cost.
        """
        settings = get_settings()
        amount = Decimal(str(chargeback.estimated_internal_cost_brl))
        if settings.commercial_qos_billing_include_opportunity_cost:
            amount += Decimal(str(chargeback.estimated_opportunity_cost_brl))
        return amount

    @staticmethod
    async def generate_qos_billing_records(db: AsyncSession, hours: int = 24) -> List[CommercialQoSBillingRecord]:
        """
        Generates billing records from chargeback data for the specified period.
        """
        settings = get_settings()
        since = utc_now() - timedelta(hours=hours)
        
        # Find chargebacks that don't have a billing record yet
        # We use a subquery to check for existence of billing records
        billing_record_subquery = select(CommercialQoSBillingRecord.chargeback_id).where(
            CommercialQoSBillingRecord.chargeback_id.isnot(None)
        )
        
        stmt = select(CommercialQueueChargeback).where(
            and_(
                CommercialQueueChargeback.created_at >= since,
                CommercialQueueChargeback.id.not_in(billing_record_subquery)
            )
        )
        
        result = await db.execute(stmt)
        chargebacks = result.scalars().all()
        
        records = []
        for cb in chargebacks:
            billable_amount = await CommercialQoSBillingService.calculate_qos_billable_amount(cb)
            
            # Skip if below min amount
            if billable_amount < Decimal(str(settings.commercial_qos_billing_min_amount_brl)):
                status = "skipped"
                error = f"Amount {billable_amount} below minimum {settings.commercial_qos_billing_min_amount_brl}"
            else:
                status = "calculated"
                error = None

            # Idempotency key: client_id + period + qos_tier + model
            idempotency_key = f"{cb.client_id}_{cb.period_start.isoformat()}_{cb.period_end.isoformat()}_{cb.qos_tier}_{cb.model}"
            
            # Check if record already exists by idempotency key
            existing_stmt = select(CommercialQoSBillingRecord).where(
                CommercialQoSBillingRecord.idempotency_key == idempotency_key
            )
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                continue

            record = CommercialQoSBillingRecord(
                client_id=cb.client_id,
                qos_tier=cb.qos_tier,
                model=cb.model,
                period_start=cb.period_start,
                period_end=cb.period_end,
                chargeback_id=cb.id,
                compute_seconds=cb.compute_seconds,
                priority_slots_consumed=cb.priority_slots_consumed,
                estimated_internal_cost_brl=Decimal(str(cb.estimated_internal_cost_brl)),
                opportunity_cost_brl=Decimal(str(cb.estimated_opportunity_cost_brl)),
                billable_amount_brl=billable_amount,
                billing_mode=settings.commercial_qos_billing_mode,
                status=status,
                idempotency_key=idempotency_key,
                error_message=error
            )
            db.add(record)
            records.append(record)
        
        await db.commit()
        return records

    @staticmethod
    async def debit_wallet_for_qos(db: AsyncSession, record: CommercialQoSBillingRecord) -> Optional[AiWalletTransaction]:
        """
        Debits the client's wallet for the QoS usage if opt-in and mode allow.
        """
        settings = get_settings()
        if settings.commercial_qos_billing_mode != "wallet_debit_opt_in" or not settings.commercial_qos_billing_debit_wallet:
            record.status = "skipped"
            record.error_message = f"Wallet debit not enabled or not in wallet_debit_opt_in mode (current mode: {settings.commercial_qos_billing_mode})"
            return None

        if record.status not in ["calculated", "failed"]:
            return None

        # Check daily limit
        daily_total = await CommercialQoSBillingService._get_daily_debit_total(db, record.client_id)
        if daily_total + record.billable_amount_brl > Decimal(str(settings.commercial_qos_billing_max_daily_debit_brl_per_client)):
            record.status = "failed"
            record.error_message = f"Daily limit exceeded. Current daily total: {daily_total}"
            return None

        try:
            # Perform debit via wallet_service
            tx = await wallet_service.debit_usage(
                db,
                client_id=record.client_id,
                amount_brl=record.billable_amount_brl,
                reference_type="qos_billing",
                reference_id=str(record.id)
            )
            
            record.status = "debited"
            record.wallet_transaction_id = tx.id
            record.processed_at = utc_now()
            return tx
        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            return None

    @staticmethod
    async def attach_to_invoice(db: AsyncSession, record: CommercialQoSBillingRecord, invoice_id: uuid.UUID) -> bool:
        """
        Attaches the billing record to an existing invoice.
        Note: Currently BillingInvoice is flat, so this just updates total_amount and association.
        """
        settings = get_settings()
        if settings.commercial_qos_billing_mode != "invoice_line_item":
            return False

        stmt = select(BillingInvoice).where(BillingInvoice.id == invoice_id)
        invoice = (await db.execute(stmt)).scalar_one_or_none()
        if not invoice:
            return False

        if record.status not in ["calculated", "failed"]:
            return False

        # Update invoice total
        invoice.total_amount += record.billable_amount_brl
        
        record.invoice_id = invoice.id
        record.status = "invoiced"
        record.processed_at = utc_now()
        
        return True

    @staticmethod
    async def _get_daily_debit_total(db: AsyncSession, client_id: uuid.UUID) -> Decimal:
        """
        Calculates total debited amount from wallet for a client in the last 24h.
        """
        since = utc_now() - timedelta(days=1)
        stmt = select(func.sum(CommercialQoSBillingRecord.billable_amount_brl)).where(
            and_(
                CommercialQoSBillingRecord.client_id == client_id,
                CommercialQoSBillingRecord.status == "debited",
                CommercialQoSBillingRecord.processed_at >= since
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or Decimal("0.000000")

    @staticmethod
    async def summarize_qos_billing(db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """
        Summarizes QoS billing data.
        """
        since = utc_now() - timedelta(hours=hours)
        stmt = select(CommercialQoSBillingRecord).where(CommercialQoSBillingRecord.created_at >= since)
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        summary = {
            "total_calculated_brl": Decimal("0.0"),
            "total_invoiced_brl": Decimal("0.0"),
            "total_debited_brl": Decimal("0.0"),
            "count_by_status": {},
            "count_by_tier": {},
            "top_clients": {}
        }
        
        for r in records:
            summary["total_calculated_brl"] += r.billable_amount_brl
            if r.status == "invoiced":
                summary["total_invoiced_brl"] += r.billable_amount_brl
            elif r.status == "debited":
                summary["total_debited_brl"] += r.billable_amount_brl
                
            summary["count_by_status"][r.status] = summary["count_by_status"].get(r.status, 0) + 1
            summary["count_by_tier"][r.qos_tier] = summary["count_by_tier"].get(r.qos_tier, 0) + 1
            
            client_id = str(r.client_id)
            summary["top_clients"][client_id] = summary["top_clients"].get(client_id, Decimal("0.0")) + r.billable_amount_brl
            
        return summary
