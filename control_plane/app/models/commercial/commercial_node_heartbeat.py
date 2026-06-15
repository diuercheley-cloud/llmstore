from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialNodeHeartbeat(Base):
    __tablename__ = "commercial_node_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True, unique=True)
    node_role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown", index=True
    )
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    process_id: Mapped[int | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="healthy", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
