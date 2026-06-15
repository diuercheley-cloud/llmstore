# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentOptimizationExperiment(Base):
    __tablename__ = "agent_optimization_experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="running")  # running|completed|failed
    metrics_baseline: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    agent = relationship("AgentDefinition")


class AgentOptimizationCandidate(Base):
    __tablename__ = "agent_optimization_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_optimization_experiments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # prompt|policy|tool_selection
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending|evaluating|completed|approved|applied|rejected
    is_improvement: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_regression: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    experiment = relationship("AgentOptimizationExperiment")
    agent = relationship("AgentDefinition")


class AgentOptimizationResult(Base):
    __tablename__ = "agent_optimization_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_optimization_candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_eval_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    metrics_delta: Mapped[dict] = mapped_column(
        JSON, default=dict
    )  # {eval_pass_rate_delta, cost_delta, latency_delta, tool_error_delta, policy_denial_delta, safety_failure_delta}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    candidate = relationship("AgentOptimizationCandidate")
    eval_run = relationship("AgentEvalRun")


class AgentPromptCandidate(Base):
    __tablename__ = "agent_prompt_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_optimization_candidates.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    improved_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate = relationship("AgentOptimizationCandidate")


class AgentPolicyCandidate(Base):
    __tablename__ = "agent_policy_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_optimization_candidates.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    policy_rules: Mapped[dict] = mapped_column(JSON, default=dict)

    candidate = relationship("AgentOptimizationCandidate")


class AgentToolSelectionCandidate(Base):
    __tablename__ = "agent_tool_selection_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_optimization_candidates.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    allowed_tools: Mapped[list] = mapped_column(JSON, default=list)

    candidate = relationship("AgentOptimizationCandidate")
