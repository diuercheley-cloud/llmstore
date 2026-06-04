import uuid
from datetime import date, datetime
from decimal import Decimal

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (
        UniqueConstraint("client_id", "period_start", "period_end", name="uq_billing_invoice_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    billing_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=True, index=True)
    pricing_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pricing_rules.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    period_start: Mapped[date] = mapped_column(Date(), nullable=False)
    period_end: Mapped[date] = mapped_column(Date(), nullable=False)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    included_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    used_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_price_per_1k_tokens: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    overage_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), default="manual_pix", nullable=False)
    payment_instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    client = relationship("Client", back_populates="invoices")
    billing_plan = relationship("BillingPlan", back_populates="invoices")
    pricing_rule = relationship("PricingRule", back_populates="invoices")
    payments = relationship("CustomerPayment", back_populates="invoice", cascade="all, delete-orphan")
