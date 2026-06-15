import uuid
from datetime import datetime
from decimal import Decimal

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialBillingDispute(Base):
    __tablename__ = "commercial_billing_disputes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    qos_billing_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("commercial_qos_billing_records.id"), nullable=True
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True
    )
    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_wallet_transactions.id"), nullable=True
    )

    dispute_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # qos_usage|wallet_debit|invoice_amount|priority_charge|other

    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    # open|under_review|resolved|rejected|credited

    claimed_amount_brl: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), default=Decimal("0.000000"), nullable=False
    )
    disputed_reason: Mapped[str] = mapped_column(Text(), nullable=False)

    admin_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    credit_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_wallet_transactions.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client = relationship("Client")
    qos_billing_record = relationship("CommercialQoSBillingRecord")
    invoice = relationship("BillingInvoice")
    wallet_transaction = relationship("AiWalletTransaction", foreign_keys=[wallet_transaction_id])
    credit_transaction = relationship("AiWalletTransaction", foreign_keys=[credit_transaction_id])
