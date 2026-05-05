import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ResponseCache(Base):
    __tablename__ = "response_cache"
    __table_args__ = (
        UniqueConstraint("cache_type", "endpoint", "model", "request_hash", name="uq_response_cache_lookup"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_type: Mapped[str] = mapped_column(String(16), default="exact", nullable=False)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(280), nullable=True)
    response_json: Mapped[str] = mapped_column(Text(), nullable=False)
    prompt_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
