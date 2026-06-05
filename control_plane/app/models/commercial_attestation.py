import uuid
from datetime import datetime, UTC

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from ..db.base import Base


class CommercialPublicAttestationRequest(Base):
    __tablename__ = "commercial_public_attestation_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_hash = Column(String(128), nullable=False, index=True)
    submitted_proof_hash = Column(String(128), nullable=True, index=True)
    source_ip = Column(String(64), nullable=True) # Masked/Anonymized
    user_agent = Column(String(512), nullable=True)
    status = Column(String(50), nullable=False, default="received") # received|verified|invalid|rejected
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialPublicAttestationResult(Base):
    __tablename__ = "commercial_public_attestation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("commercial_public_attestation_requests.id"), nullable=False)
    verification_type = Column(String(50), nullable=False) # receipt|proof|timeline|witness_quorum|checkpoint
    result = Column(String(50), nullable=False) # valid|invalid|partial
    result_json = Column(JSON, nullable=True) # Sanitized
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
