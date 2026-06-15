from datetime import datetime
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class SovereignDataZone(Base):
    __tablename__ = "sovereign_data_zones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    zone_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    export_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    retention_policy: Mapped[str] = mapped_column(String(255), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DataLineageRecord(Base):
    __tablename__ = "data_lineage_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DataRetentionRule(Base):
    __tablename__ = "data_retention_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    retention_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retention_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    enforcement_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="advisory")
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DataExportGovernanceRecord(Base):
    __tablename__ = "data_export_governance_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    export_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sanitized: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    export_status: Mapped[str] = mapped_column(String(32), nullable=False, default="advisory")
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
