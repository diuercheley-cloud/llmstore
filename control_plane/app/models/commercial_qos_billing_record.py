import uuid
from datetime import datetime
from decimal import Decimal

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialQoSBillingRecord(Base):
    __tablename__ = "commercial_qos_billing_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_qos_billing_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    qos_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    chargeback_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_queue_chargebacks.id"), nullable=True)
    
    compute_seconds: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    priority_slots_consumed: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    
    estimated_internal_cost_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    opportunity_cost_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    billable_amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    
    billing_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    # calculated|invoiced|debited|skipped|failed
    status: Mapped[str] = mapped_column(String(24), default="calculated", nullable=False, index=True)
    
    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_wallet_transactions.id"), nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True)
    
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)

    client = relationship("Client")
    chargeback = relationship("CommercialQueueChargeback")
    wallet_transaction = relationship("AiWalletTransaction")
    invoice = relationship("BillingInvoice")
