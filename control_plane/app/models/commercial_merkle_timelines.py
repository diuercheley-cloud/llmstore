import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialMerkleTimeline(Base):
    __tablename__ = "commercial_merkle_timelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timeline_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    leaf_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    merkle_root: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    previous_timeline_root: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    timeline_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="building",
        index=True,
    )
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialMerkleLeaf(Base):
    __tablename__ = "commercial_merkle_leaves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_merkle_timelines.id"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    leaf_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    leaf_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialExecutionProof(Base):
    __tablename__ = "commercial_execution_proofs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    receipt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_inference_receipts.id"),
        nullable=True,
        index=True,
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_merkle_timelines.id"),
        nullable=False,
        index=True,
    )
    proof_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    proof_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    proof_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
