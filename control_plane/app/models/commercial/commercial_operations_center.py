import uuid
from datetime import datetime, UTC

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CommercialOperationsCenterEvent(Base):
    __tablename__ = "commercial_operations_center_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(JSON, nullable=True)
    hash = Column(String(128), nullable=False, index=True)
    parent_hash = Column(String(128), nullable=True, index=True) # For hash chaining
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialCryptographicTrustSnapshot(Base):
    __tablename__ = "commercial_cryptographic_trust_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_data = Column(JSON, nullable=False)
    immutable_hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
