import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from ..db.base import Base


class CommercialConfidentialRuntimeProfile(Base):
    __tablename__ = "commercial_confidential_runtime_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_name = Column(String(128), nullable=False)
    client_id = Column(String(64), nullable=True, index=True)
    enabled = Column(Boolean, default=True)
    
    require_encrypted_input = Column(Boolean, default=False)
    require_encrypted_output = Column(Boolean, default=False)
    prohibit_prompt_logging = Column(Boolean, default=True)
    prohibit_response_logging = Column(Boolean, default=True)
    require_runtime_attestation = Column(Boolean, default=False)
    require_model_trust = Column(Boolean, default=True)
    
    max_retention_seconds = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialConfidentialInferenceSession(Base):
    __tablename__ = "commercial_confidential_inference_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(64), nullable=True, index=True)
    request_id = Column(String(128), nullable=True, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("commercial_confidential_runtime_profiles.id"), nullable=True)
    encryption_key_id = Column(String(128), nullable=True)
    
    input_mode = Column(String(32), default="plaintext") # plaintext|encrypted|hash_only
    output_mode = Column(String(32), default="plaintext") # plaintext|encrypted|hash_only
    attestation_status = Column(String(32), default="unknown") # trusted|untrusted|unknown
    model_trust_state = Column(String(64), nullable=True)
    retention_policy_applied = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class CommercialConfidentialRuntimeAuditEvent(Base):
    __tablename__ = "commercial_confidential_runtime_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("commercial_confidential_inference_sessions.id"), nullable=True)
    event_type = Column(String(64), nullable=False, index=True)
    # confidential_session_started, encrypted_input_received, encrypted_output_generated,
    # plaintext_logging_blocked, retention_policy_applied, attestation_required, attestation_failed
    
    summary = Column(Text, nullable=True)
    immutable_hash = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
