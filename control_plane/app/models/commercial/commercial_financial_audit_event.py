import uuid
from datetime import datetime
from decimal import Decimal

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialFinancialAuditEvent(Base):
    __tablename__ = "commercial_financial_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # qos_billing_created, qos_wallet_debited, qos_invoice_attached, dispute_opened, dispute_resolved, reconciliation_mismatch, manual_credit, manual_adjustment
    
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    
    related_record_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    amount_brl: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    client = relationship("Client")
