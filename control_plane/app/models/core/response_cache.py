import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class ResponseCache(Base):
    __tablename__ = "response_cache"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "cache_type",
            "endpoint_type",
            "model",
            "request_hash",
            name="uq_response_cache_lookup",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    cache_type: Mapped[str] = mapped_column(String(16), default="exact", nullable=False)
    endpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    normalized_prompt_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    request_fingerprint: Mapped[str | None] = mapped_column(String(280), nullable=True)
    prompt_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    response_json: Mapped[str] = mapped_column(Text(), nullable=False)
    semantic_embedding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
