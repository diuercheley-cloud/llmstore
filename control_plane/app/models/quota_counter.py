import uuid
from datetime import date, datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class QuotaCounter(Base):
    __tablename__ = "quota_counters"
    __table_args__ = (UniqueConstraint("client_id", "period_start", "period_type", name="uq_quota_counter_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    used_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_tts_chars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_embeddings_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_embeddings_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
