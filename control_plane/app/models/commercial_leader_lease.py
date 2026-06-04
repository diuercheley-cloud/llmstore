from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialLeaderLease(Base):
    __tablename__ = "commercial_leader_leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    leader_role: Mapped[str] = mapped_column(sa.String(32), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    lease_token: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False, index=True)
    lease_acquired_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, index=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict | None] = mapped_column(sa.JSON(), nullable=True)

    __table_args__ = (
        sa.Index(
            "uq_commercial_leader_leases_active_role",
            "cluster_id",
            "leader_role",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
            sqlite_where=sa.text("status = 'active'"),
        ),
    )
