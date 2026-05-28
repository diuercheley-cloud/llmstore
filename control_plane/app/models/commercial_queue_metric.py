import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialQueueMetric(Base):
    __tablename__ = "commercial_queue_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    qos_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    queue_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_wait_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    p95_wait_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_wait_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    jobs_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_throttled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starvation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sla_queue_violations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
