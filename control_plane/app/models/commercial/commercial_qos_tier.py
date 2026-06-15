from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialQoSTier(Base):
    __tablename__ = "commercial_qos_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Lower is higher priority? Let's follow Enterprise > Premium > ...

    target_latency_ms: Mapped[int] = mapped_column(Integer, default=500)
    max_p95_latency_ms: Mapped[int] = mapped_column(Integer, default=2000)
    min_margin_percent: Mapped[float] = mapped_column(Numeric(8, 2), default=5.0)
    max_cost_per_request_brl: Mapped[float] = mapped_column(Numeric(14, 8), default=0.50)

    allow_cloud: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_cross_cluster: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_degraded_cluster: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_fallback_local: Mapped[bool] = mapped_column(Boolean, default=True)

    queue_priority: Mapped[int] = mapped_column(Integer, default=100)  # Higher is higher priority
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    streaming_timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)

    quality_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    degradation_policy: Mapped[str] = mapped_column(
        String(32), default="best_effort"
    )  # block|fallback_local|cheapest|best_effort

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
