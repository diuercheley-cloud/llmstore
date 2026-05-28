import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialRetrievalProof(Base):
    __tablename__ = "commercial_retrieval_proofs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_retrieval_receipts.id"),
        nullable=False,
        index=True,
    )
    vault_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_rag_vaults.id"),
        nullable=False,
        index=True,
    )
    timeline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_merkle_timelines.id"),
        nullable=True,
        index=True,
    )
    proof_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    policy_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    lineage_root_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    retrieval_sent_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    merkle_root: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proof_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    export_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialContextLineage(Base):
    __tablename__ = "commercial_context_lineages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_proof_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_retrieval_proofs.id"),
        nullable=False,
        index=True,
    )
    parent_lineage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_context_lineages.id"),
        nullable=True,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    node_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialRetrievalMerkleLeaf(Base):
    __tablename__ = "commercial_retrieval_merkle_leaves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_proof_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_retrieval_proofs.id"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    leaf_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    leaf_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialRetrievalReplayRecord(Base):
    __tablename__ = "commercial_retrieval_replay_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_proof_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_retrieval_proofs.id"),
        nullable=False,
        index=True,
    )
    replay_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    replay_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    drift_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
