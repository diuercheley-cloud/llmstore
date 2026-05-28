from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class SovereignMetricRecord(Base):
    __tablename__ = "sovereign_metric_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    metric_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_value: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class SovereignTraceRecord(Base):
    __tablename__ = "sovereign_trace_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    trace_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    trace_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trace_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class OperationalTimeline(Base):
    __tablename__ = "operational_timelines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    timeline_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    timeline_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timeline_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

