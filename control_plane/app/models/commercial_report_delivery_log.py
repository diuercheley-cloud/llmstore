from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommercialReportDeliveryLog(Base):
    __tablename__ = "commercial_report_delivery_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    report_format: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    recipients_json: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    delivery_mode: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    delivery_status: Mapped[str] = mapped_column(sa.String(20), nullable=False, index=True)
    smtp_host: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    subject: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    attachment_names_json: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    retries: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
