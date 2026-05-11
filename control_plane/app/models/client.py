import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    billing_status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    billing_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=True, index=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    daily_token_quota: Mapped[int] = mapped_column(Integer, default=100_000_000, nullable=False)
    weekly_token_quota: Mapped[int] = mapped_column(Integer, default=500_000_000, nullable=False)
    monthly_token_quota: Mapped[int] = mapped_column(Integer, default=1_000_000_000, nullable=False)
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=131072, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=32768, nullable=False)
    allowed_models_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ip_allowlist_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ip_blocklist_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    api_keys = relationship("ApiKey", back_populates="client", cascade="all, delete-orphan")
    billing_plan = relationship("BillingPlan", back_populates="clients")
    invoices = relationship("BillingInvoice", back_populates="client", cascade="all, delete-orphan")
    payments = relationship("CustomerPayment", back_populates="client", cascade="all, delete-orphan")
