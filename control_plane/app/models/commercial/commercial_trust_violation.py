import uuid
from datetime import UTC, datetime

from app.db.base import Base
from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID


class CommercialTrustViolation(Base):
    __tablename__ = "commercial_trust_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_type = Column(
        String(100), nullable=False, index=True
    )  # hash_mismatch|lineage_break|integrity_failure
    severity = Column(String(50), nullable=False)  # critical|high|medium|low
    detected_at = Column(DateTime, default=lambda: datetime.now(UTC))
    details_json = Column(JSON, nullable=True)
    remediation_status = Column(
        String(50), nullable=False, default="pending"
    )  # pending|resolved|ignored
    evidence_hash = Column(String(128), nullable=True)
