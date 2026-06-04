# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AgentUncertaintyEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_uncertainty_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(64), nullable=False) # none|research|hitl|uncertain_response
    policy_triggered: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False) # {evidence, contradiction, etc}
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentConfidenceScore(Base):
    # Owner: agent-platform
    __tablename__ = "agent_confidence_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    score: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentEvidenceGap(Base):
    # Owner: agent-platform
    __tablename__ = "agent_evidence_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    missing_information: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentUncertaintyPolicy(Base):
    # Owner: agent-platform
    __tablename__ = "agent_uncertainty_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    min_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    auto_research_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    hitl_on_low_confidence: Mapped[bool] = mapped_column(Boolean, default=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
