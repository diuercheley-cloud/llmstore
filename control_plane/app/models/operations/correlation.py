import hashlib
import json
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def compute_deterministic_hash(*, fields: dict, version: str = "v1") -> str:
    """Computes a deterministic SHA-256 hash for a dictionary of fields."""
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{version}:{raw}".encode("utf-8")).hexdigest()

class OperationalCorrelation(Base):
    __tablename__ = "operational_correlations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_domains_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # List or dict of domains
    correlation_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    correlation_score: Mapped[float] = mapped_column(Float(), default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float(), default=0.0, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class CorrelatedOperationalEvent(Base):
    __tablename__ = "correlated_operational_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operational_correlations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class OperationalTrustLink(Base):
    __tablename__ = "operational_trust_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_node: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trust_relation: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float(), default=0.0, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
