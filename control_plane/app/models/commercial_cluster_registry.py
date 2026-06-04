from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialClusterRegistry(Base):
    __tablename__ = "commercial_cluster_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), nullable=False, default="local", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    tenant_scope_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Phase 19: Geo-Aware Routing
    latitude: Mapped[float | None] = mapped_column(server_default=None, nullable=True)
    longitude: Mapped[float | None] = mapped_column(server_default=None, nullable=True)
    datacenter: Mapped[str | None] = mapped_column(String(64), nullable=True)
    continent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    avg_public_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geo_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Phase 18: Cross-Cluster Forwarding
    forwarding_enabled: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    forwarding_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    forwarding_public_key: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    forwarding_jwt_audience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forwarding_require_mtls: Mapped[bool] = mapped_column(server_default="false", default=False, nullable=False)
    forwarding_status: Mapped[str] = mapped_column(String(32), server_default="healthy", default="healthy", nullable=False)
    forwarding_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )
