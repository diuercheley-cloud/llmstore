import hashlib
import json
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional

from app.models.commercial_financial_audit_event import CommercialFinancialAuditEvent
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class FinancialAuditTrailService:
    @staticmethod
    def calculate_hash(
        previous_hash: str,
        event_type: str,
        amount_brl: Optional[Decimal],
        timestamp: datetime
    ) -> str:
        """
        Calculates a SHA256 hash for the audit event, chaining it to the previous one.
        """
        payload = {
            "previous_hash": previous_hash,
            "event_type": event_type,
            "amount_brl": str(amount_brl) if amount_brl is not None else "0.000000",
            "timestamp": timestamp.isoformat()
        }
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    @staticmethod
    async def get_latest_hash(db: AsyncSession) -> str:
        """
        Retrieves the hash of the most recent audit event.
        Returns a 'genesis' hash if no events exist.
        """
        stmt = select(CommercialFinancialAuditEvent).order_by(desc(CommercialFinancialAuditEvent.created_at)).limit(1)
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()
        
        if not latest:
            return "0" * 64  # Genesis hash
        
        return latest.immutable_hash

    @staticmethod
    async def create_audit_event(
        db: AsyncSession,
        event_type: str,
        client_id: Optional[uuid.UUID] = None,
        related_record_type: Optional[str] = None,
        related_record_id: Optional[str] = None,
        amount_brl: Optional[Decimal] = None,
        metadata_json: Optional[dict] = None
    ) -> CommercialFinancialAuditEvent:
        """
        Creates a new audit event with an immutable hash chain.
        """
        
        previous_hash = await FinancialAuditTrailService.get_latest_hash(db)
        
        # We'll use the app's utc_now if possible
        from app.core.time import utc_now
        timestamp = utc_now()

        immutable_hash = FinancialAuditTrailService.calculate_hash(
            previous_hash=previous_hash,
            event_type=event_type,
            amount_brl=amount_brl,
            timestamp=timestamp
        )

        event = CommercialFinancialAuditEvent(
            event_type=event_type,
            client_id=client_id,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
            amount_brl=amount_brl,
            metadata_json=metadata_json,
            immutable_hash=immutable_hash,
            created_at=timestamp
        )
        db.add(event)
        # Note: Caller is responsible for commit to ensure atomicity with the related record change
        return event

    @staticmethod
    async def validate_audit_chain(db: AsyncSession) -> bool:
        """
        Validates the entire audit chain hash by recalculating hashes from genesis.
        """
        stmt = select(CommercialFinancialAuditEvent).order_by(CommercialFinancialAuditEvent.created_at)
        result = await db.execute(stmt)
        events = result.scalars().all()

        current_previous_hash = "0" * 64
        for event in events:
            expected_hash = FinancialAuditTrailService.calculate_hash(
                previous_hash=current_previous_hash,
                event_type=event.event_type,
                amount_brl=event.amount_brl,
                timestamp=event.created_at
            )
            
            if event.immutable_hash != expected_hash:
                return False
            
            current_previous_hash = event.immutable_hash
            
        return True
