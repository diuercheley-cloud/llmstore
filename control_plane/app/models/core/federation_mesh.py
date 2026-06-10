import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class MeshMergePolicy(str, Enum):
    LWW = "last_write_wins"
    MANUAL = "manual"
    CRDT = "crdt_deterministic"


class ClusterNode(Base):
    __tablename__ = "mesh_cluster_nodes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # unique node name
    public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_self: Mapped[bool] = mapped_column(Boolean, default=False)
    logical_clock: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FederationPeer(Base):
    __tablename__ = "mesh_federation_peers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str] = mapped_column(String(128), ForeignKey("mesh_cluster_nodes.id"), unique=True)
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    trust_level: Mapped[str] = mapped_column(String(32), default="trusted")
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    node = relationship("ClusterNode")


class SyncCommit(Base):
    __tablename__ = "mesh_sync_commits"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    author_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    logical_clock: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConflictRecord(Base):
    __tablename__ = "mesh_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    peer_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conflicting_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|resolved
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
