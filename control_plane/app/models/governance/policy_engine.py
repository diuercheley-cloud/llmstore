import json
from datetime import datetime
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class DeterministicPolicy(Base):
    __tablename__ = "deterministic_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    policy_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    policy_dsl: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    policy_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    def dsl_json(self) -> dict:
        return json.loads(self.policy_dsl)


class PolicyEvaluationResult(Base):
    __tablename__ = "policy_evaluation_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deterministic_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    evaluation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class PolicyBundle(Base):
    __tablename__ = "deterministic_policy_bundles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    bundle_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    policy_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class PolicyConflict(Base):
    __tablename__ = "deterministic_policy_conflicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deterministic_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resolution_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
