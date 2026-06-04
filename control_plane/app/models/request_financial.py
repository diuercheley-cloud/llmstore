import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class RequestFinancial(Base):
    __tablename__ = "request_financials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    request_log_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    api_key_prefix: Mapped[str | None] = mapped_column(String(12), nullable=True)
    endpoint_type: Mapped[str] = mapped_column(String(32), default="chat")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    token_count_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tokens_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_cost_usd: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True, default=0.0)
    provider_cost_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True, default=0.0)
    customer_price_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True, default=0.0)
    gross_profit_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True, default=0.0)
    margin_percent: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True, default=0.0)
    fx_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True, default=5.0)
    fx_rate_source: Mapped[str | None] = mapped_column(String(32), default="manual_env")
    pricing_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", lazy="joined")
