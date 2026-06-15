from datetime import datetime
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class DeterministicEventContract(Base):
    __tablename__ = "deterministic_event_contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    compatibility_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="compatible", index=True
    )
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class DeterministicEventRecord(Base):
    __tablename__ = "deterministic_event_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class EventSchemaCompatibility(Base):
    __tablename__ = "event_schema_compatibility"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_contract_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deterministic_event_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    compatibility_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
