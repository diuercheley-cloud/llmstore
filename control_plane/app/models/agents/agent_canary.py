# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AgentCanaryAssignment(Base):
    # Owner: agent-platform
    __tablename__ = "agent_canary_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canary_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False
    )

    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    traffic_percentage: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # For real traffic split if enabled
    is_shadow: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # If True, runs in parallel without affecting response

    status: Mapped[str] = mapped_column(
        String(32), default="active"
    )  # active|paused|promoted|retired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AgentShadowRun(Base):
    # Owner: agent-platform
    __tablename__ = "agent_shadow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_canary_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )

    primary_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shadow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    status: Mapped[str] = mapped_column(String(32), default="running")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AgentCanaryComparison(Base):
    # Owner: agent-platform
    __tablename__ = "agent_canary_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shadow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shadow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metrics: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # {latency_diff, cost_diff, success_match, tool_divergence}
    findings: Mapped[list] = mapped_column(JSON, nullable=False)  # List of qualitative differences

    is_regression: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AgentCanaryPromotionReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_canary_promotion_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_canary_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # approve|reject
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    eval_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
