from datetime import datetime
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class SovereignBackupManifest(Base):
    __tablename__ = "sovereign_backup_manifests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    backup_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    backup_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    backup_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    recovery_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recovery_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    recovery_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RecoveryVerificationResult(Base):
    __tablename__ = "recovery_verification_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    recovery_plan_id: Mapped[str] = mapped_column(String(64), ForeignKey("recovery_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RestoreRequest(Base):
    __tablename__ = "restore_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    backup_id: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    requester: Mapped[str] = mapped_column(String(120), nullable=False)
    approver: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


