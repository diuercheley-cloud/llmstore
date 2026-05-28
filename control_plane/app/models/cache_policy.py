import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CachePolicy(Base):
    __tablename__ = "cache_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True, unique=True)
    billing_plan_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    semantic_cache_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    cache_sensitive_data_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_price_discount_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    max_cache_entries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
