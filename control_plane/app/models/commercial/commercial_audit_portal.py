from __future__ import annotations

import uuid
from datetime import date, datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialPortalAuditAccessLog(Base):
    __tablename__ = "commercial_portal_audit_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    ip_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_sanitized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    client = relationship("Client")


class CommercialPortalSavedReport(Base):
    __tablename__ = "commercial_portal_saved_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    export_format: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    client = relationship("Client")
