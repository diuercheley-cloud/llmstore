# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentDefinition(Base):
    # Owner: agent-platform
    __tablename__ = "agent_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|active|paused|deprecated
    risk_level: Mapped[str] = mapped_column(String(32), default="low")  # low|medium|high|critical
    allowed_tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    policy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    memory_policy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=10)
    max_runtime_seconds: Mapped[int] = mapped_column(Integer, default=300)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_cost_brl: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    prompt_template_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    runs = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan")


class AgentRun(Base):
    # Owner: agent-platform
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)  # queued|running|waiting_approval|completed|failed|cancelled|paused
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_brl: Mapped[float] = mapped_column(Float, default=0.0)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_reads_count: Mapped[int] = mapped_column(Integer, default=0)
    replans_count: Mapped[int] = mapped_column(Integer, default=0)
    approval_wait_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    multimodal_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("multimodal_assets.id", ondelete="SET NULL"), nullable=True)

    agent = relationship("AgentDefinition", back_populates="runs")
    steps = relationship("AgentRunStep", back_populates="run", cascade="all, delete-orphan")
    events = relationship("AgentRunEvent", back_populates="run", cascade="all, delete-orphan")
    checkpoints = relationship("AgentRunCheckpoint", back_populates="run", cascade="all, delete-orphan")
    receipts = relationship("AgentRunReceipt", back_populates="run", cascade="all, delete-orphan")


class AgentRunStep(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(64), nullable=False)  # model_call|tool_call|memory_read|memory_write|approval|handoff|final
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="success")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    policy_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentRun", back_populates="steps")


class AgentRunEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentRun", back_populates="events")


class AgentRunCheckpoint(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    checkpoint_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    state_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentRun", back_populates="checkpoints")


class AgentRunReceipt(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receipt_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentRun", back_populates="receipts")


class AgentRegistryEntry(Base):
    # Owner: agent-platform
    __tablename__ = "agent_registry_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1.0")
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    business_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_surface_status: Mapped[str] = mapped_column(String(32), default="internal")  # supported|beta|experimental|internal
    risk_level: Mapped[str] = mapped_column(String(32), default="low")  # low|medium|high|critical
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_tenants: Mapped[list | None] = mapped_column(JSON, nullable=True)
    allowed_models: Mapped[list | None] = mapped_column(JSON, nullable=True)
    allowed_tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|review|approved|active|paused|deprecated|archived
    eval_baseline: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("AgentVersion", back_populates="agent_entry", cascade="all, delete-orphan")
    promotions = relationship("AgentPromotion", back_populates="agent_entry", cascade="all, delete-orphan")
    deprecations = relationship("AgentDeprecation", back_populates="agent_entry", cascade="all, delete-orphan")
    lifecycle_events = relationship("AgentLifecycleEvent", back_populates="agent_entry", cascade="all, delete-orphan")


class AgentVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    semantic_version: Mapped[str] = mapped_column(String(64), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    allowed_models: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_entry = relationship("AgentRegistryEntry", back_populates="versions")


class AgentPromotion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[str] = mapped_column(String(128), nullable=False)
    promotion_step_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_entry = relationship("AgentRegistryEntry", back_populates="promotions")


class AgentDeprecation(Base):
    # Owner: agent-platform
    __tablename__ = "agent_deprecations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    deprecated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    replacement_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_entry = relationship("AgentRegistryEntry", back_populates="deprecations")


class AgentLifecycleEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_entry = relationship("AgentRegistryEntry", back_populates="lifecycle_events")


class AgentTool(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="0.1.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # retrieval|filesystem_safe|database_read|...
    input_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")  # low|medium|high|critical
    side_effect_level: Mapped[str] = mapped_column(String(32), default="none")  # none|read|write|destructive|external
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retry_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    dry_run_supported: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_supported: Mapped[bool] = mapped_column(Boolean, default=False)
    docs_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    data_boundary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="tenant", nullable=False)  # global|tenant|private
    max_cost_brl: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_calls_per_run: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    approval_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tenant_allowlist: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    environment_allowlist: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("AgentToolVersion", back_populates="agent_tool", cascade="all, delete-orphan")
    permissions = relationship("AgentToolPermission", back_populates="agent_tool", cascade="all, delete-orphan")
    invocations = relationship("AgentToolInvocation", back_populates="agent_tool", cascade="all, delete-orphan")
    safety_reviews = relationship("AgentToolSafetyReview", back_populates="agent_tool", cascade="all, delete-orphan")


class AgentToolVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tool_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    side_effect_level: Mapped[str] = mapped_column(String(32), default="none")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="tenant", nullable=False)
    max_cost_brl: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_calls_per_run: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    approval_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_tool = relationship("AgentTool", back_populates="versions")


class AgentToolPermission(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tool_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    granted_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_tool = relationship("AgentTool", back_populates="permissions")


class AgentToolInvocation(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tool_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="success")  # success|failed|dry_run|rolled_back
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rollback: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_tool = relationship("AgentTool", back_populates="invocations")


class AgentToolSafetyReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tool_safety_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_tool_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tools.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # approved|rejected
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent_tool = relationship("AgentTool", back_populates="safety_reviews")


class AgentApprovalRequest(Base):
    # Owner: agent-platform
    __tablename__ = "agent_approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_invocation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(64), default="admin_write")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending|approved|rejected|expired|cancelled
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sanitized_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Advanced HITL fields
    escalation_status: Mapped[str] = mapped_column(String(32), default="none") # none, escalated
    escalated_to_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_batch_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    decisions = relationship("AgentApprovalDecision", back_populates="approval_request", cascade="all, delete-orphan")


class AgentEvalSuite(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_suites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    cases = relationship("AgentEvalCase", back_populates="suite", cascade="all, delete-orphan")
    runs = relationship("AgentEvalRun", back_populates="suite", cascade="all, delete-orphan")


class AgentEvalCase(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    prohibited_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    expected_tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    max_cost_brl: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    max_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assertions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    suite = relationship("AgentEvalSuite", back_populates="cases")
    results = relationship("AgentEvalResult", back_populates="case", cascade="all, delete-orphan")


class AgentEvalRun(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|completed|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    suite = relationship("AgentEvalSuite", back_populates="runs")
    results = relationship("AgentEvalResult", back_populates="run", cascade="all, delete-orphan")


class AgentEvalResult(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    assertion_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost_brl: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_id_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # Reference to actual AgentRun
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentEvalRun", back_populates="results")
    case = relationship("AgentEvalCase", back_populates="results")


class AgentEvalBaseline(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    set_by: Mapped[str] = mapped_column(String(128), nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

class AgentLLMJudgeRun(Base):
    # Owner: agent-platform
    __tablename__ = "agent_llm_judge_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_results.id", ondelete="CASCADE"), nullable=False, index=True)
    judge_model: Mapped[str] = mapped_column(String(128), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentRedTeamCase(Base):
    # Owner: agent-platform
    __tablename__ = "agent_red_team_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    attack_type: Mapped[str] = mapped_column(String(64), nullable=False) # jailbreak, injection, exfiltration, unsafe_tool
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    expected_denial: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentABEvalRun(Base):
    # Owner: agent-platform
    __tablename__ = "agent_ab_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id"), nullable=False)
    agent_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    winner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentEvalPairwiseResult(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_pairwise_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ab_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_ab_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_a: Mapped[str] = mapped_column(Text, nullable=False)
    response_b: Mapped[str] = mapped_column(Text, nullable=False)
    preference: Mapped[str] = mapped_column(String(8), nullable=False) # A, B, Tie
    rationale: Mapped[str] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict) # cost, latency, safety
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentEvalDataset(Base):

    # Owner: agent-platform
    __tablename__ = "agent_eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("AgentEvalDatasetVersion", back_populates="dataset", cascade="all, delete-orphan")


class AgentEvalDatasetVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    cases_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset = relationship("AgentEvalDataset", back_populates="versions")


class AgentEvalGateResult(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_gate_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    eval_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    tool_misuse_rate: Mapped[float] = mapped_column(Float, nullable=False)
    policy_denial_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_brl: Mapped[float] = mapped_column(Float, nullable=False)
    max_steps_exceeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    secret_leak_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cross_tenant_access_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentEvalRegressionResult(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_regression_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    eval_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    regression_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metric_diffs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentPromotionGateResult(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_promotion_gates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    target_status: Mapped[str] = mapped_column(String(32), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    gate_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_gate_results.id", ondelete="SET NULL"), nullable=True, index=True)
    regression_result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_regression_results.id", ondelete="SET NULL"), nullable=True, index=True)
    audit_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemoryPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)  # short_term|long_term|episodic|semantic|preference|operational
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    redaction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    encryption_required: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_export: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentMemoryCollection(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemoryItem(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_memory_collections.id", ondelete="SET NULL"), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    redaction_status: Mapped[str] = mapped_column(String(32), default="none")  # none|pending|completed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMemoryAccessEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_access_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    memory_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_memory_items.id", ondelete="CASCADE"), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)  # read|write|delete|export
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemoryRetentionJob(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_retention_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|completed|failed
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_deleted: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentPlan(Base):
    # Owner: agent-platform
    __tablename__ = "agent_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|approved|executing|completed|failed|cancelled
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    tasks = relationship("AgentTask", back_populates="plan", cascade="all, delete-orphan")
    cost_estimates = relationship("AgentPlanCostEstimate", back_populates="plan", cascade="all, delete-orphan")


class AgentTask(Base):
    # Owner: agent-platform
    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)  # tool_call|model_call|memory_op|sub_task
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|blocked|waiting_approval|completed|failed|skipped
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    compensation_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "agent_compensation_actions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_agent_tasks_compensation_action_id",
        ),
        nullable=True,
    )
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    plan = relationship("AgentPlan", back_populates="tasks")
    dependencies = relationship("AgentTaskDependency", foreign_keys="[AgentTaskDependency.task_id]", back_populates="task", cascade="all, delete-orphan")
    attempts = relationship("AgentTaskAttempt", back_populates="task", cascade="all, delete-orphan")


class AgentTaskDependency(Base):
    # Owner: agent-platform
    __tablename__ = "agent_task_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)

    task = relationship("AgentTask", foreign_keys=[task_id], back_populates="dependencies")


class AgentTaskAttempt(Base):
    # Owner: agent-platform
    __tablename__ = "agent_task_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # running|completed|failed
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("AgentTask", back_populates="attempts")


class AgentCompensationAction(Base):
    # Owner: agent-platform
    __tablename__ = "agent_compensation_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|executed|failed
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentHandoffPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_handoff_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    allowed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_handoffs_per_run: Mapped[int] = mapped_column(Integer, default=5)
    allowed_context_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_boundary_mode: Mapped[str] = mapped_column(String(32), default="strict") # strict|relaxed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentCollaborationSession(Base):
    # Owner: agent-platform
    __tablename__ = "agent_collaboration_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    root_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    handoff_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active") # active|completed|terminated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentHandoffEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_handoff_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_collaboration_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    target_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    context_keys: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMarketplaceEntry(Base):
    # Owner: agent-platform
    __tablename__ = "agent_marketplace_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False) # support, operations, billing, etc.
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    versions = relationship("AgentBundleVersion", back_populates="entry", cascade="all, delete-orphan")


class AgentBundleVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_marketplace_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    min_platform_version: Mapped[str] = mapped_column(String(64), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    entry = relationship("AgentMarketplaceEntry", back_populates="versions")
    installs = relationship("AgentBundleInstall", back_populates="version")


class AgentBundleInstall(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_installs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="installed") # installed|enabled|disabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    version = relationship("AgentBundleVersion", back_populates="installs")


class AgentBundleTrustReport(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_trust_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    trust_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    signer_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    report_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentApprovalDecision(Base):
    # Owner: agent-platform
    __tablename__ = "agent_approval_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_approval_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # approved|rejected|request_changes
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    approval_request = relationship("AgentApprovalRequest", back_populates="decisions")


class AgentApprovalPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_approval_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)  # risk_level | tool_call | agent_run | always
    risk_level_threshold: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    required_role: Mapped[str] = mapped_column(String(64), default="admin_write")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentMemoryConsent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, revoked
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMemoryRetentionPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expire_after_days: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentMemoryRedactionEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_redaction_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_memory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    redacted_types: Mapped[str] = mapped_column(String(256), nullable=False)  # csv of types like email, secret, key
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemoryIndex(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_indexes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_memory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    index_status: Mapped[str] = mapped_column(String(32), default="pending") # pending, completed, failed
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-serialized embedding vector
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentMemorySearchEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_search_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    query_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemoryDeleteRequest(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_delete_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    memory_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, completed, failed
    items_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMemoryExportRequest(Base):
    # Owner: agent-platform
    __tablename__ = "agent_memory_export_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=True, index=True)
    memory_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, completed, failed
    export_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AgentIncident(Base):
    # Owner: agent-platform
    __tablename__ = "agent_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open") # open, acknowledged, resolved
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False) # e.g., repeated_tool_failure, run_stuck
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AgentIncidentEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_incident_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentRunMetrics(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_errors: Mapped[int] = mapped_column(Integer, default=0)
    total_policy_denials: Mapped[int] = mapped_column(Integer, default=0)
    total_memory_reads: Mapped[int] = mapped_column(Integer, default=0)
    total_memory_writes: Mapped[int] = mapped_column(Integer, default=0)
    total_approval_waits: Mapped[int] = mapped_column(Integer, default=0)
    total_approval_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    total_handoffs: Mapped[int] = mapped_column(Integer, default=0)
    run_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentRunCosts(Base):
    # Owner: agent-platform
    __tablename__ = "agent_run_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_brl: Mapped[float] = mapped_column(Float, default=0.0)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_reads_count: Mapped[int] = mapped_column(Integer, default=0)
    replans_count: Mapped[int] = mapped_column(Integer, default=0)
    approval_wait_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentTraceSpan(Base):
    # Owner: agent-platform
    __tablename__ = "agent_trace_spans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    span_type: Mapped[str] = mapped_column(String(64), nullable=False) # run, step, tool, model
    status: Mapped[str] = mapped_column(String(32), default="ok")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    events_json: Mapped[list] = mapped_column(JSON, default=list)

class AgentTimelineEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False) # run.created, tool.called, etc.
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)

class AgentPolicyDecision(Base):
    # Owner: agent-platform
    __tablename__ = "agent_policy_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False) # tool_call|memory_read|memory_write|handoff|planner_exec
    subject: Mapped[str] = mapped_column(String(256), nullable=False) # e.g. tool name, memory type
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id"), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    result: Mapped[str] = mapped_column(String(32), nullable=False) # allow|deny|require_approval|...
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("AgentRun")


class AgentGuardrailEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_guardrail_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    guardrail_type: Mapped[str] = mapped_column(String(64), nullable=False) # jailbreak, pii, secret, etc.
    detection_point: Mapped[str] = mapped_column(String(64), nullable=False) # input, model_output, tool_output
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sanitized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentGuardrailDecision(Base):
    # Owner: agent-platform
    __tablename__ = "agent_guardrail_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False) # allow, redact, require_human_review, block
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardrail_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentEvalFailure(Base):
    # Owner: agent-platform
    __tablename__ = "agent_eval_failures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    failure_type: Mapped[str] = mapped_column(String(64), nullable=False) # regression, secret_leak, tool_error, etc.
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentIncidentLink(Base):
    # Owner: agent-platform
    __tablename__ = "agent_incident_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    linked_incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(32), default="related") # related, causal, duplicate
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentSLOWindow(Base):
    # Owner: agent-platform
    __tablename__ = "agent_slo_windows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    window_type: Mapped[str] = mapped_column(String(32), nullable=False) # 1h, 24h, 7d, 30d
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    success_runs: Mapped[int] = mapped_column(Integer, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0)
    slo_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict) # detailed SLO metrics like p95 latency
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentTraceLink(Base):
    # Owner: agent-platform
    __tablename__ = "agent_trace_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    linked_trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    link_reason: Mapped[str] = mapped_column(String(64), nullable=False) # handoff, tool_callback, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentEnvironmentPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_environment_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True) # None for global
    environment: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # dev, test, staging, production, sovereign, managed
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AgentEphemeralCredential(Base):
    # Owner: agent-platform
    __tablename__ = "agent_ephemeral_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(128), nullable=False) # tool name or resource path
    credential_type: Mapped[str] = mapped_column(String(32), nullable=False) # bearer, basic, aws_sigv4
    credential_value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentRBACEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_rbac_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False) # permission.denied, role.assigned
    status: Mapped[str] = mapped_column(String(32), nullable=False) # success, denied
    permission_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentPolicyException(Base):
    # Owner: agent-platform
    __tablename__ = "agent_policy_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_type: Mapped[str] = mapped_column(String(64), nullable=False) # sovereign_tool_block, destructive_tool_requirement
    exception_reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentBundleSignature(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_signatures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    signature_type: Mapped[str] = mapped_column(String(32), default="ed25519")
    signature_value: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    signed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentBundleProvenance(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_provenance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    build_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    builder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentBundleCompatibility(Base):
    # Owner: agent-platform
    __tablename__ = "agent_bundle_compatibility"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_version_min: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_version_max: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required_flags_json: Mapped[list] = mapped_column(JSON, default=list)
    conflicting_flags_json: Mapped[list] = mapped_column(JSON, default=list)

class AgentAdapterPromotionReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_adapter_promotion_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adapter_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    security_check_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), default="pending") # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentPromptBaseline(Base):
    # Owner: agent-platform
    __tablename__ = "agent_prompt_baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    eval_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_eval_runs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active") # active|superseded
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentPromotionGate(Base):
    # Owner: agent-platform
    __tablename__ = "agent_promotion_gates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    target_status: Mapped[str] = mapped_column(String(32), nullable=False)
    eval_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    security_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    compatibility_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|passed|failed
    rollback_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentPublisherProfile(Base):
    # Owner: agent-platform
    __tablename__ = "agent_publisher_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(128), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentPublicationReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_publication_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_bundle_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending, approved, rejected
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_assessment_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentCatalogItem(Base):
    # Owner: agent-platform
    __tablename__ = "agent_catalog_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # agent|tool|prompt|eval_dataset|policy|planner
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft") # draft|active|deprecated|production
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("AgentCatalogVersion", back_populates="catalog_item", cascade="all, delete-orphan")
    rollbacks = relationship("AgentCatalogRollback", back_populates="catalog_item", cascade="all, delete-orphan")


class AgentCatalogVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_catalog_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    configuration_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    compatibility: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    catalog_item = relationship("AgentCatalogItem", back_populates="versions")


class AgentCatalogRollback(Base):
    # Owner: agent-platform
    __tablename__ = "agent_catalog_rollbacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_catalog_items.id", ondelete="CASCADE"), nullable=False, index=True)
    from_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_catalog_versions.id"), nullable=False)
    to_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_catalog_versions.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    catalog_item = relationship("AgentCatalogItem", back_populates="rollbacks")

class AgentDelegationPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_delegation_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_depth_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentSharedMemoryPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_shared_memory_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_group_id: Mapped[str] = mapped_column(String(128), nullable=False) # logical group for memory sharing
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, default=True)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentA2ARegistration(Base):
    __tablename__ = "agent_a2a_registrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_url: Mapped[str | None] = mapped_column(String(512), nullable=True) # remote A2A endpoint
    auth_token: Mapped[str] = mapped_column(String(256), nullable=False) # Authorization token for incoming/outgoing A2A calls
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict) # discovery info (e.g. tools, description)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agent = relationship("AgentDefinition")


class AgentStepCacheEntry(Base):
    # Owner: agent-platform
    __tablename__ = "agent_step_cache_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    step_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentPlanCostEstimate(Base):
    # Owner: agent-platform
    __tablename__ = "agent_plan_cost_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_tool_cost_brl: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_runtime_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_approval_cost_brl: Mapped[float] = mapped_column(Float, default=0.0)
    total_estimated_cost_brl: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    plan = relationship("AgentPlan", back_populates="cost_estimates")

