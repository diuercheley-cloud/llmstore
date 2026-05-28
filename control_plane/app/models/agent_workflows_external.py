# Owner: Platform Operations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentWorkflowWebhookSubscription(Base):
    __tablename__ = "agent_workflow_webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    secret_token: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active") # active|triggered|expired
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentWorkflowPollingJob(Base):
    __tablename__ = "agent_workflow_polling_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="GET")
    headers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    max_attempts: Mapped[int] = mapped_column(Integer, default=10)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=1.5)
    stop_condition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict) # e.g. {"path": "status", "value": "done"}
    next_poll_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|active|completed|failed|timed_out
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentWorkflowExternalEvent(Base):
    __tablename__ = "agent_workflow_external_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_source: Mapped[str] = mapped_column(String(64), nullable=False) # webhook|polling
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    sanitized_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
