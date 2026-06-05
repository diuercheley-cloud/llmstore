import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional

from app.db.base import Base
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class MemoryScope(str, Enum):
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    RELATIONAL = "relational"
    VECTOR = "vector"
    GRAPH = "graph"
    WORKFLOW_STATE = "workflow_state"


class MemoryEventType(str, Enum):
    CREATED = "memory.created"
    UPDATED = "memory.updated"
    FORGOTTEN = "memory.forgotten"
    REDACTED = "memory.redacted"
    ACCESSED = "memory.accessed"
    COMPACTED = "memory.compacted"


class MemoryEvent(Base):
    __tablename__ = "agent_memory_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    scope: Mapped[MemoryScope] = mapped_column(String(32), nullable=False)
    event_type: Mapped[MemoryEventType] = mapped_column(String(32), nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Event Sourcing / Hash Chain
    previous_event_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Logical Clock (CRDT-ready)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    logical_counter: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # Scoring for Forgetting Curves
    importance_score: Mapped[float] = mapped_column(Float, default=1.0)
    decay_score: Mapped[float] = mapped_column(Float, default=0.0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MemorySnapshot(Base):
    """Compact representation of current state at a given event hash."""
    __tablename__ = "agent_memory_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scope: Mapped[MemoryScope] = mapped_column(String(32), nullable=False)
    
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
