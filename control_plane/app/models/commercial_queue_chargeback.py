import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialQueueChargeback(Base):
    __tablename__ = "commercial_queue_chargebacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    qos_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    compute_seconds: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    queue_wait_seconds: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    priority_slots_consumed: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    
    estimated_opportunity_cost_brl: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    estimated_internal_cost_brl: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    chargeback_amount_brl: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
