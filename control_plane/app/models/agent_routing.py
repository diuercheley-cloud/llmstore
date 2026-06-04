import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AgentModelCapability(Base):
    # Owner: agent-platform
    __tablename__ = "agent_model_capabilities"

    model_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    supports_tool_calling: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_json_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_input: Mapped[float] = mapped_column(Float, nullable=False)  # Cost per 1k tokens
    cost_output: Mapped[float] = mapped_column(Float, nullable=False) # Cost per 1k tokens
    latency_class: Mapped[str] = mapped_column(String(32), nullable=False) # ultra-low|low|medium|high
    quality_tier: Mapped[int] = mapped_column(Integer, nullable=False) # 1-5
    recommended_step_classes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentRoutingPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_routing_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentCostQualityProfile(Base):
    # Owner: agent-platform
    __tablename__ = "agent_cost_quality_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    max_cost_input: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_cost_output: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_quality_tier: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AgentStepRoutingDecision(Base):
    # Owner: agent-platform
    __tablename__ = "agent_step_routing_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_run_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    step_class: Mapped[str] = mapped_column(String(64), nullable=False)
    chosen_model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_applied: Mapped[str | None] = mapped_column(String(128), nullable=True)
    budget_spent: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    routing_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships could be added if needed, but keeping it simple for now as per AgentRunStep pattern.
