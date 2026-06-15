# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class FederatedMemoryPeer(Base):
    # Owner: agent-platform
    __tablename__ = "federated_memory_peers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    cluster_name: Mapped[str] = mapped_column(String(256))

    endpoint_url: Mapped[str] = mapped_column(String(512))
    trust_level: Mapped[str] = mapped_column(
        String(32), default="standard"
    )  # low|standard|high|sovereign

    data_residency_region: Mapped[str] = mapped_column(String(64))  # e.g., us-east-1, eu-west-1
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class FederatedMemorySummary(Base):
    # Owner: agent-platform
    __tablename__ = "federated_memory_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    origin_cluster_id: Mapped[str] = mapped_column(String(128))

    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    original_memory_id: Mapped[str] = mapped_column(String(128))  # ID in origin cluster

    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class FederatedGraphFact(Base):
    # Owner: agent-platform
    __tablename__ = "federated_graph_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)

    subject: Mapped[str] = mapped_column(String(256))
    predicate: Mapped[str] = mapped_column(String(256))
    object: Mapped[str] = mapped_column(String(256))

    origin_cluster_id: Mapped[str] = mapped_column(String(128))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RemoteMemoryReference(Base):
    # Owner: agent-platform
    __tablename__ = "remote_memory_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_tenant_id: Mapped[str] = mapped_column(String(128), index=True)

    remote_cluster_id: Mapped[str] = mapped_column(String(128))
    remote_memory_id: Mapped[str] = mapped_column(String(128))

    reference_type: Mapped[str] = mapped_column(
        String(32), default="pointer"
    )  # proxy|summary_only|full_link
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class FederatedSyncEvent(Base):
    # Owner: agent-platform
    __tablename__ = "federated_sync_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    peer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("federated_memory_peers.id")
    )

    event_type: Mapped[str] = mapped_column(
        String(64)
    )  # sync_start|sync_complete|sync_failed|revocation_propagation
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
