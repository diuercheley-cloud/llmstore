import uuid
from datetime import datetime, UTC

from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID


class PlatformReleaseBaseline(Base):
    __tablename__ = "platform_release_baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_version = Column(String(50), nullable=False, index=True)
    baseline_scope = Column(JSON, nullable=False) # List of components/phases
    validation_snapshot_hash = Column(String(64), nullable=False)
    release_hash = Column(String(64), nullable=False, unique=True)
    replay_safe = Column(Boolean, default=True)
    immutable_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class ValidationSnapshot(Base):
    __tablename__ = "validation_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    baseline_id = Column(UUID(as_uuid=True), ForeignKey("platform_release_baselines.id"), nullable=False)
    validation_scope = Column(String(100), nullable=False) # smoke | full
    validation_result = Column(JSON, nullable=False)
    validation_hash = Column(String(64), nullable=False)
    immutable_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class ReleaseReceipt(Base):
    __tablename__ = "release_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    baseline_id = Column(UUID(as_uuid=True), ForeignKey("platform_release_baselines.id"), nullable=False)
    receipt_type = Column(String(50), nullable=False) # internal | audit | compliance
    payload_hash = Column(String(64), nullable=False)
    immutable_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(UTC))
