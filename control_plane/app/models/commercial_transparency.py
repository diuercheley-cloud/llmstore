import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from ..db.base import Base


class CommercialTransparencyGossipPeer(Base):
    __tablename__ = "commercial_transparency_gossip_peers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    peer_id = Column(String(255), unique=True, nullable=False, index=True)
    peer_type = Column(String(50), nullable=False)  # cluster|witness|auditor|offline
    endpoint = Column(String(512), nullable=True)
    public_key = Column(String(1024), nullable=True)
    status = Column(String(50), default="active")  # active|disabled|offline
    last_seen_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialTransparencyGossipRecord(Base):
    __tablename__ = "commercial_transparency_gossip_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_peer_id = Column(String(255), nullable=False, index=True)
    target_peer_id = Column(String(255), nullable=True, index=True)
    timeline_root = Column(String(255), nullable=True)
    timeline_hash = Column(String(255), nullable=True)
    checkpoint_hash = Column(String(255), nullable=True)
    gossip_type = Column(String(50), nullable=False)  # push|pull|manual|offline
    verification_status = Column(String(50), default="unknown")  # valid|invalid|conflict|unknown
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialConsistencyCheckpoint(Base):
    __tablename__ = "commercial_consistency_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkpoint_type = Column(String(50), nullable=False)  # merkle_timeline|receipt_chain|witness_quorum|policy_bundle
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    root_hash = Column(String(255), nullable=False, index=True)
    signed_checkpoint = Column(String(1024), nullable=True)
    witness_summary_json = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialTransparencySplitViewAlert(Base):
    __tablename__ = "commercial_transparency_split_view_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(100), nullable=False)  # root_mismatch|missing_timeline|witness_conflict|checkpoint_conflict
    severity = Column(String(50), nullable=False)  # low|medium|high|critical
    expected_hash = Column(String(255), nullable=True)
    observed_hash = Column(String(255), nullable=True)
    summary = Column(String(1024), nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
