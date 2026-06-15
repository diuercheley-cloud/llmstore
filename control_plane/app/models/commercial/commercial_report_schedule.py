from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialReportSchedule(Base):
    __tablename__ = "commercial_report_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True, index=True)
    frequency: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="monthly")
    day_of_month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    hour_utc: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=8)
    recipients_json: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    format: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="html")
    filters_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(sa.String(120), nullable=True)
