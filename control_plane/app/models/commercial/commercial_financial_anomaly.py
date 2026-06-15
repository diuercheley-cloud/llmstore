import uuid
from datetime import datetime
from decimal import Decimal

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialFinancialAnomaly(Base):
    __tablename__ = "commercial_financial_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # revenue_spike|revenue_drop|cost_spike|margin_drop|wallet_debit_spike|qos_billing_spike|dispute_spike
    anomaly_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # low|medium|high|critical
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    observed_value_brl: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), default=Decimal("0.000000"), nullable=False
    )
    expected_value_brl: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), default=Decimal("0.000000"), nullable=False
    )
    deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # open|acknowledged|resolved|ignored
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)

    explanation: Mapped[str | None] = mapped_column(Text(), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    client = relationship("Client")
