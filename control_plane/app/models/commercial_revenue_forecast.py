import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class CommercialRevenueForecast(Base):
    __tablename__ = "commercial_revenue_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # revenue|cost|margin|wallet_debit|qos_billing
    forecast_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    qos_tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    forecast_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    predicted_amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    lower_bound_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    upper_bound_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    
    # low|medium|high
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    
    # moving_average|ewma|linear_trend
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    client = relationship("Client")
