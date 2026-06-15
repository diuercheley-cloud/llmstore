from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialFederatedAggregate(Base):
    __tablename__ = "commercial_federated_aggregates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_cluster_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    bucket_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    bucket_minutes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    requests_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_revenue_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    estimated_cost_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_revenue_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_cost_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_margin_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
