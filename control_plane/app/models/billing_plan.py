import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_token_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    weekly_token_quota: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_token_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    allow_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # RAG Limits
    rag_max_documents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_max_storage_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_max_pages_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_max_queries_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    price_brl: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_models_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    clients = relationship("Client", back_populates="billing_plan")
    pricing_rules = relationship("PricingRule", back_populates="billing_plan", cascade="all, delete-orphan")
    invoices = relationship("BillingInvoice", back_populates="billing_plan")
