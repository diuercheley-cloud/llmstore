# Owner: Platform Operations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentFlowDefinition(Base):
    __tablename__ = "agent_flow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("AgentFlowVersion", back_populates="flow_definition", cascade="all, delete-orphan")

class AgentFlowVersion(Base):
    __tablename__ = "agent_flow_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_flow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    # The actual graph can be stored here as JSON for simplicity in prototype, 
    # but we will also create node/edge tables as requested.
    graph_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    flow_definition = relationship("AgentFlowDefinition", back_populates="versions")
    nodes = relationship("AgentFlowNode", back_populates="flow_version", cascade="all, delete-orphan")
    edges = relationship("AgentFlowEdge", back_populates="flow_version", cascade="all, delete-orphan")

class AgentFlowNode(Base):
    __tablename__ = "agent_flow_nodes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True) # Usually node ID from frontend
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_flow_versions.id", ondelete="CASCADE"), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False) # agent|tool_call|etc
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)

    flow_version = relationship("AgentFlowVersion", back_populates="nodes")

class AgentFlowEdge(Base):
    __tablename__ = "agent_flow_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_flow_versions.id", ondelete="CASCADE"), primary_key=True)
    source_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    condition: Mapped[str | None] = mapped_column(String(256), nullable=True)

    flow_version = relationship("AgentFlowVersion", back_populates="edges")

class AgentDebugSession(Base):
    __tablename__ = "agent_debug_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    flow_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_flow_versions.id"))
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active") # active|completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentDebugEvent(Base):
    __tablename__ = "agent_debug_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_debug_sessions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
