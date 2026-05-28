import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class CommercialFinancialReconciliation(Base):
    __tablename__ = "commercial_financial_reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # qos_billing|wallet|invoice|chargeback
    
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    expected_amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    actual_amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    delta_amount_brl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    discrepancy_percent: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(24), default="matched", nullable=False, index=True)
    # matched|warning|mismatch|investigating|resolved
    
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client = relationship("Client")
