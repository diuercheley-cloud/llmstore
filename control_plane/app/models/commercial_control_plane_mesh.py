import uuid

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String


class CommercialMeshNode(Base):
    __tablename__ = "commercial_mesh_nodes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    region = Column(String, index=True)
    mode = Column(String, default="multi_region") # single_region, multi_region, sovereign_partitioned, airgap_sync
    public_key = Column(String)
    is_leader = Column(Boolean, default=False)
    status = Column(String, default="active") # active, inactive, partitioned, syncing
    metadata_ = Column(JSON, default={})
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class CommercialMeshConsensusEvent(Base):
    __tablename__ = "commercial_mesh_consensus_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    term = Column(Integer, index=True)
    event_type = Column(String) # leader_election, state_commit, configuration_change
    proposer_node_id = Column(String, ForeignKey("commercial_mesh_nodes.id"))
    payload = Column(JSON)
    signature = Column(String)
    quorum_reached = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

class CommercialMeshReplicationLog(Base):
    __tablename__ = "commercial_mesh_replication_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String, ForeignKey("commercial_mesh_nodes.id"))
    log_index = Column(Integer, index=True)
    operation = Column(String)
    target_entity = Column(String)
    target_id = Column(String)
    changes = Column(JSON)
    hash_signature = Column(String) # immutability
    applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

class CommercialMeshHealthState(Base):
    __tablename__ = "commercial_mesh_health_states"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String, ForeignKey("commercial_mesh_nodes.id"))
    peer_node_id = Column(String)
    latency_ms = Column(Integer)
    last_heartbeat = Column(DateTime)
    status = Column(String) # healthy, degraded, unreachable
    created_at = Column(DateTime, default=utc_now)

class CommercialMeshPartitionEvent(Base):
    __tablename__ = "commercial_mesh_partition_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    partition_id = Column(String, index=True)
    isolated_nodes = Column(JSON)
    mode_fallback = Column(String) # e.g. sovereign_partitioned
    detected_at = Column(DateTime, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)
    resolution_details = Column(JSON, nullable=True)
