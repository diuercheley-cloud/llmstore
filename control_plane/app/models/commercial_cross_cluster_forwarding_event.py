from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class CommercialCrossClusterForwardingEvent(Base):
    __tablename__ = "commercial_cross_cluster_forwarding_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_cluster_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_cluster_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_mode: Mapped[str] = mapped_column(String(32), nullable=False) # stream | non_stream
    result: Mapped[str] = mapped_column(String(64), nullable=False) # forwarded | fallback_local | blocked | circuit_open | timeout
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bytes_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
