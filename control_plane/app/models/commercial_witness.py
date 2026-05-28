from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..db.base import Base

class CommercialWitness(Base):
    __tablename__ = "commercial_witnesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    witness_name = Column(String(255), nullable=False)
    witness_type = Column(String(50), nullable=False) # internal|external|offline|airgap
    public_key = Column(Text, nullable=True)
    endpoint = Column(String(512), nullable=True)
    status = Column(String(50), default="active") # active|disabled|offline|untrusted
    trust_level = Column(String(50), default="medium") # low|medium|high
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialWitnessSignature(Base):
    __tablename__ = "commercial_witness_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timeline_id = Column(UUID(as_uuid=True), ForeignKey("commercial_merkle_timelines.id"), nullable=False)
    witness_id = Column(UUID(as_uuid=True), ForeignKey("commercial_witnesses.id"), nullable=False)
    merkle_root = Column(String(255), nullable=False)
    signature = Column(Text, nullable=False)
    signature_algorithm = Column(String(50), nullable=False)
    signed_at = Column(DateTime, default=datetime.utcnow)
    verification_status = Column(String(50), default="pending") # pending|valid|invalid|expired
    metadata_json = Column(JSON, default={})

    timeline = relationship("CommercialMerkleTimeline")
    witness = relationship("CommercialWitness")

class CommercialWitnessQuorumPolicy(Base):
    __tablename__ = "commercial_witness_quorum_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    timeline_type = Column(String(100), nullable=False) # inference_receipts|...
    required_signatures = Column(Integer, default=1)
    allowed_witnesses_json = Column(JSON, default=[]) # list of witness IDs or types
    require_external_witness = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialWitnessAuditEvent(Base):
    __tablename__ = "commercial_witness_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    witness_id = Column(UUID(as_uuid=True), nullable=True)
    timeline_id = Column(UUID(as_uuid=True), nullable=True)
    summary = Column(Text, nullable=False)
    immutable_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
