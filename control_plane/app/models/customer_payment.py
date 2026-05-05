import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class CustomerPayment(Base):
    __tablename__ = "customer_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), default="manual_pix", nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    invoice = relationship("BillingInvoice", back_populates="payments")
    client = relationship("Client", back_populates="payments")
