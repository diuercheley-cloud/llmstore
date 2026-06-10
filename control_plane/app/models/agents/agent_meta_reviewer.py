# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentMetaReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_meta_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|completed|failed
    overall_decision: Mapped[str] = mapped_column(String(32), default="allow") # allow|require_revision|require_human_approval|block
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings = relationship("AgentMetaReviewFinding", back_populates="review", cascade="all, delete-orphan")

class AgentMetaReviewFinding(Base):
    # Owner: agent-platform
    __tablename__ = "agent_meta_review_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_meta_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    checker_type: Mapped[str] = mapped_column(String(64), nullable=False) # hallucination|policy_drift|ethical_risk
    severity: Mapped[str] = mapped_column(String(32), nullable=False) # low|medium|high|critical
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    review = relationship("AgentMetaReview", back_populates="findings")

class AgentMetaReviewDecision(Base):
    # Owner: agent-platform
    __tablename__ = "agent_meta_review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_meta_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    blocking_action_taken: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
