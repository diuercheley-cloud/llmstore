# Owner: agent-platform
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentRunSnapshot(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_snapshots"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    full_state: Mapped[dict] = mapped_column(JSON, nullable=False) # Snapshot of agent_state
    memory_references: Mapped[list] = mapped_column(JSON, nullable=False) # IDs of memory items accessed
    tool_receipts: Mapped[list] = mapped_column(JSON, nullable=False)
    policy_decisions: Mapped[list] = mapped_column(JSON, nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentDebugReplay(Base):
    # Owner: agent-platform
    __tablename__ = "agent_debug_replays"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    replay_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_run_snapshots.id"))
    step_rewind_to: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="active") # active|completed|failed
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentDebugStateEdit(Base):
    # Owner: agent-platform
    __tablename__ = "agent_debug_state_edits"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    replay_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_debug_replays.id", ondelete="CASCADE"), nullable=False, index=True)
    
    field_path: Mapped[str] = mapped_column(String(256), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    editor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentDebugSession(Base):
    # Owner: agent-platform
    __tablename__ = "agent_debug_sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active") # active, paused, stopped
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    is_live_stepping: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AgentBreakpoint(Base):
    # Owner: agent-platform
    __tablename__ = "agent_breakpoints"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False) # step_type, tool_name, policy_denial, approval_request, error
    target: Mapped[str | None] = mapped_column(String(255), nullable=True) # e.g. tool name
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentDebugStepEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_debug_step_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_debug_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False) # step_start, step_end, breakpoint_hit
    state_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
