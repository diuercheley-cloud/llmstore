import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_billing_dispute import CommercialBillingDispute
from app.models.ai_wallet import AiWalletTransaction
from app.services.billing import wallet_service
from app.services.billing.financial_audit_trail import FinancialAuditTrailService
from app.services.notifications.revenue_escalations import evaluate_escalation_policies


class DisputeManagementService:
    @staticmethod
    async def open_dispute(
        db: AsyncSession,
        client_id: uuid.UUID,
        dispute_type: str,
        claimed_amount_brl: Decimal,
        disputed_reason: str,
        qos_billing_record_id: Optional[uuid.UUID] = None,
        invoice_id: Optional[uuid.UUID] = None,
        wallet_transaction_id: Optional[uuid.UUID] = None
    ) -> CommercialBillingDispute:
        """
        Opens a new billing dispute.
        """
        dispute = CommercialBillingDispute(
            client_id=client_id,
            qos_billing_record_id=qos_billing_record_id,
            invoice_id=invoice_id,
            wallet_transaction_id=wallet_transaction_id,
            dispute_type=dispute_type,
            status="open",
            claimed_amount_brl=claimed_amount_brl,
            disputed_reason=disputed_reason
        )
        db.add(dispute)
        await db.flush()
        
        await FinancialAuditTrailService.create_audit_event(
            db,
            event_type="dispute_opened",
            client_id=client_id,
            related_record_type="CommercialBillingDispute",
            related_record_id=str(dispute.id), # This might be problematic before flush, but SQLAlchemy usually handles it or we flush
            amount_brl=claimed_amount_brl,
            metadata_json={"dispute_type": dispute_type}
        )
        
        recent_stmt = select(func.count(CommercialBillingDispute.id)).where(
            CommercialBillingDispute.client_id == client_id,
            CommercialBillingDispute.created_at >= utc_now() - timedelta(hours=24),
        )
        recent_count = (await db.execute(recent_stmt)).scalar() or 0
        if recent_count >= 3:
            await evaluate_escalation_policies(
                db,
                source_type="dispute",
                source_id=dispute.id,
                severity="high",
                summary=f"Mass disputes detected for client {client_id}",
                recommendation="Review dispute volume, billing deltas, and customer impact.",
                metadata={"dispute_type": dispute_type, "recent_disputes_24h": recent_count},
                trigger_type="mass_disputes",
            )

        await db.commit()
        return dispute

    @staticmethod
    async def review_dispute(db: AsyncSession, dispute_id: uuid.UUID, admin_notes: str) -> bool:
        """
        Marks a dispute as under review.
        """
        stmt = select(CommercialBillingDispute).where(CommercialBillingDispute.id == dispute_id)
        dispute = (await db.execute(stmt)).scalar_one_or_none()
        
        if not dispute or dispute.status != "open":
            return False
            
        dispute.status = "under_review"
        dispute.admin_notes = admin_notes
        dispute.updated_at = utc_now()
        
        await db.commit()
        return True

    @staticmethod
    async def resolve_dispute(
        db: AsyncSession,
        dispute_id: uuid.UUID,
        resolution_notes: str,
        credit_amount_brl: Decimal = Decimal("0.000000")
    ) -> bool:
        """
        Resolves a dispute, optionally providing a credit.
        """
        stmt = select(CommercialBillingDispute).where(CommercialBillingDispute.id == dispute_id)
        dispute = (await db.execute(stmt)).scalar_one_or_none()
        
        if not dispute or dispute.status in ["resolved", "rejected", "credited"]:
            return False
            
        dispute.resolution_notes = resolution_notes
        dispute.resolved_at = utc_now()
        dispute.updated_at = utc_now()
        
        if credit_amount_brl > 0:
            # Issue manual credit via wallet_service
            tx = await wallet_service.credit_manual(
                db,
                client_id=dispute.client_id,
                amount_brl=credit_amount_brl,
                reason=f"Dispute Resolution {dispute.id}",
                created_by="system_admin" # Or pass admin id
            )
            await db.flush()
            dispute.credit_transaction_id = tx.id
            dispute.status = "credited"
            
            await FinancialAuditTrailService.create_audit_event(
                db,
                event_type="dispute_resolved",
                client_id=dispute.client_id,
                related_record_type="CommercialBillingDispute",
                related_record_id=str(dispute.id),
                amount_brl=credit_amount_brl,
                metadata_json={"resolution": "credited", "notes": resolution_notes}
            )
        else:
            dispute.status = "resolved"
            await FinancialAuditTrailService.create_audit_event(
                db,
                event_type="dispute_resolved",
                client_id=dispute.client_id,
                related_record_type="CommercialBillingDispute",
                related_record_id=str(dispute.id),
                amount_brl=Decimal("0.000000"),
                metadata_json={"resolution": "resolved_no_credit", "notes": resolution_notes}
            )
            
        await db.commit()
        return True

    @staticmethod
    async def reject_dispute(db: AsyncSession, dispute_id: uuid.UUID, resolution_notes: str) -> bool:
        """
        Rejects a dispute.
        """
        stmt = select(CommercialBillingDispute).where(CommercialBillingDispute.id == dispute_id)
        dispute = (await db.execute(stmt)).scalar_one_or_none()
        
        if not dispute or dispute.status in ["resolved", "rejected", "credited"]:
            return False
            
        dispute.status = "rejected"
        dispute.resolution_notes = resolution_notes
        dispute.resolved_at = utc_now()
        dispute.updated_at = utc_now()
        
        await FinancialAuditTrailService.create_audit_event(
            db,
            event_type="dispute_resolved",
            client_id=dispute.client_id,
            related_record_type="CommercialBillingDispute",
            related_record_id=str(dispute.id),
            amount_brl=Decimal("0.000000"),
            metadata_json={"resolution": "rejected", "notes": resolution_notes}
        )
        
        await db.commit()
        return True

    @staticmethod
    async def create_manual_credit(
        db: AsyncSession,
        client_id: uuid.UUID,
        amount_brl: Decimal,
        reason: str,
        admin_id: str
    ) -> AiWalletTransaction:
        """
        Creates a manual credit for a client.
        """
        settings = get_settings()
        if not settings.commercial_financial_manual_credit_enabled:
            raise ValueError("Manual credit is disabled by configuration")
            
        tx = await wallet_service.credit_manual(
            db,
            client_id=client_id,
            amount_brl=amount_brl,
            reason=reason[:128],
            created_by=admin_id
        )
        await db.flush()
        
        await FinancialAuditTrailService.create_audit_event(
            db,
            event_type="manual_credit",
            client_id=client_id,
            related_record_type="AiWalletTransaction",
            related_record_id=str(tx.id),
            amount_brl=amount_brl,
            metadata_json={"reason": reason, "admin_id": admin_id}
        )
        
        await db.commit()
        return tx

    @staticmethod
    async def summarize_disputes(db: AsyncSession) -> Dict[str, Any]:
        """
        Summarizes disputes status.
        """
        stmt = select(
            CommercialBillingDispute.status,
            func.count(CommercialBillingDispute.id),
            func.sum(CommercialBillingDispute.claimed_amount_brl)
        ).group_by(CommercialBillingDispute.status)
        
        result = await db.execute(stmt)
        summary = result.all()
        
        return {
            str(status): {"count": count, "total_claimed": float(total_claimed or 0)}
            for status, count, total_claimed in summary
        }
