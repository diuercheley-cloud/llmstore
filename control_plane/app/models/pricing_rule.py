import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    billing_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    overage_price_per_1k_tokens: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    billing_plan = relationship("BillingPlan", back_populates="pricing_rules")
    invoices = relationship("BillingInvoice", back_populates="pricing_rule")
