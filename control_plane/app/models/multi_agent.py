# Owner: Platform Operations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentTeam(Base):
    __tablename__ = "agent_teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topology: Mapped[str] = mapped_column(String(64), nullable=False) # hierarchical|debate|peer_to_peer
    owner_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active") # active|paused|deprecated
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict) # max_rounds, max_depth, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    members = relationship("AgentTeamMember", back_populates="team", cascade="all, delete-orphan")
    runs = relationship("AgentTeamRun", back_populates="team", cascade="all, delete-orphan")

class AgentTeamMember(Base):
    __tablename__ = "agent_team_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False) # manager|specialist|critic|proposer|synthesizer
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    team = relationship("AgentTeam", back_populates="members")

class AgentTeamRun(Base):
    __tablename__ = "agent_team_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running") # running|completed|failed|cancelled
    input_goal: Mapped[str] = mapped_column(Text, nullable=False)
    output_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    team = relationship("AgentTeam", back_populates="runs")
    messages = relationship("AgentTeamMessage", back_populates="run", cascade="all, delete-orphan")
    delegations = relationship("AgentTeamDelegation", back_populates="run", cascade="all, delete-orphan")
    traces = relationship("AgentTeamTrace", back_populates="run", cascade="all, delete-orphan")

class AgentTeamMessage(Base):
    __tablename__ = "agent_team_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_team_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True)
    recipient_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(64), nullable=False) # proposal|critique|instruction|result
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentTeamRun", back_populates="messages")

class AgentTeamDelegation(Base):
    __tablename__ = "agent_team_delegations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_team_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    child_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|active|completed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentTeamRun", back_populates="delegations")

class AgentSharedWorkspace(Base):
    __tablename__ = "agent_shared_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    team_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_team_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(256), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AgentTeamTrace(Base):
    __tablename__ = "agent_team_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_team_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentTeamRun", back_populates="traces")
