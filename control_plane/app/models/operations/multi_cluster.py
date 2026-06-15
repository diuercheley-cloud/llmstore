import uuid
from datetime import UTC, datetime

from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, unique=True)
    cluster_type = Column(String)  # primary, standby, edge, isolated
    status = Column(String, default="active")  # active, maintenance, degraded, offline
    base_url = Column(String)
    location = Column(String, nullable=True)  # e.g. aws-us-east-1, local-dc-1
    is_managed = Column(Boolean, default=True)

    metadata_json = Column(JSON, default={})

    health_snapshots = relationship("ClusterHealthSnapshot", back_populates="cluster")
    failover_events = relationship("ClusterFailoverEvent", back_populates="cluster")


class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = Column(String, ForeignKey("clusters.id"))
    node_id = Column(String)  # RuntimeNode ID
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC))


class ClusterHealthSnapshot(Base):
    __tablename__ = "cluster_health_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = Column(String, ForeignKey("clusters.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    health_score = Column(Float)
    metrics_json = Column(JSON)  # CPU, Memory, GPU, Error Rate

    cluster = relationship("Cluster", back_populates="health_snapshots")


class ClusterRoutingPolicy(Base):
    __tablename__ = "cluster_routing_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    policy_type = Column(String)  # weight_based, latency_based, location_based
    config = Column(JSON)  # weights per cluster, etc.
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class ClusterFailoverEvent(Base):
    __tablename__ = "cluster_failover_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = Column(String, ForeignKey("clusters.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    from_status = Column(String)
    to_status = Column(String)
    reason = Column(Text)
    is_automatic = Column(Boolean, default=False)
    operator_id = Column(String, nullable=True)

    cluster = relationship("Cluster", back_populates="failover_events")


class ClusterMaintenanceWindow(Base):
    __tablename__ = "cluster_maintenance_windows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = Column(String, ForeignKey("clusters.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    description = Column(Text)
    is_active = Column(Boolean, default=True)


class ClusterSyncEvent(Base):
    __tablename__ = "cluster_sync_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_cluster_id = Column(String, ForeignKey("clusters.id"))
    target_cluster_id = Column(String, ForeignKey("clusters.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    sync_type = Column(String)  # CONFIG, METRICS, HEARBEAT
    status = Column(String)  # success, failed
    payload_size_bytes = Column(Integer)
    error_message = Column(Text, nullable=True)
