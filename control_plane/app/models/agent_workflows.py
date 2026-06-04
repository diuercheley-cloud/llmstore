# Owner: Platform Operations
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentWorkflow(Base):
    __tablename__ = "agent_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    runs = relationship("AgentWorkflowRun", back_populates="workflow", cascade="all, delete-orphan")

class AgentWorkflowRun(Base):
    __tablename__ = "agent_workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    workflow_definition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    current_state: Mapped[str] = mapped_column(String(64), nullable=False)
    state_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    next_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    workflow = relationship("AgentWorkflow", back_populates="runs")
    events = relationship("AgentWorkflowEvent", back_populates="run", cascade="all, delete-orphan")
    timers = relationship("AgentWorkflowTimer", back_populates="run", cascade="all, delete-orphan")
    signals = relationship("AgentWorkflowSignal", back_populates="run", cascade="all, delete-orphan")
    webhook_waits = relationship("AgentWorkflowWebhookWait", back_populates="run", cascade="all, delete-orphan")

class AgentWorkflowEvent(Base):
    __tablename__ = "agent_workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentWorkflowRun", back_populates="events")

class AgentWorkflowTimer(Base):
    __tablename__ = "agent_workflow_timers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    timer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|fired|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentWorkflowRun", back_populates="timers")

class AgentWorkflowSignal(Base):
    __tablename__ = "agent_workflow_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_name: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|consumed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentWorkflowRun", back_populates="signals")

class AgentWorkflowWebhookWait(Base):
    __tablename__ = "agent_workflow_webhook_waits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    webhook_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="waiting") # waiting|received|expired
    received_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentWorkflowRun", back_populates="webhook_waits")

class AgentWorkflowDefinition(Base):
    __tablename__ = "agent_workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    nodes = relationship("AgentWorkflowNode", back_populates="workflow_definition", cascade="all, delete-orphan")
    edges = relationship("AgentWorkflowEdge", back_populates="workflow_definition", cascade="all, delete-orphan")

class AgentWorkflowNode(Base):
    __tablename__ = "agent_workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False) # Unique within a workflow
    node_type: Mapped[str] = mapped_column(String(64), nullable=False) # task, condition, parallel_fanout, fanin_join, subworkflow, approval, timer, webhook_wait
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    workflow_definition = relationship("AgentWorkflowDefinition", back_populates="nodes")

class AgentWorkflowEdge(Base):
    __tablename__ = "agent_workflow_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    from_node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    to_node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    workflow_definition = relationship("AgentWorkflowDefinition", back_populates="edges")

class AgentWorkflowParallelGroup(Base):
    __tablename__ = "agent_workflow_parallel_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    fanout_node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active") # active, completed, failed
    parallelism_limit: Mapped[int] = mapped_column(Integer, default=0) # 0 for no limit
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_policy: Mapped[str] = mapped_column(String(32), default="fail_fast") # fail_fast, continue, compensate
    branches_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_branches_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_branches_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentSubworkflowRun(Base):
    __tablename__ = "agent_subworkflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    subworkflow_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_definitions.id"), nullable=False)
    subworkflow_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True) # ID of the run in agent_workflow_runs
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending, running, completed, failed
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AgentWorkflowLock(Base):
    __tablename__ = "agent_workflow_locks"

    lock_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
