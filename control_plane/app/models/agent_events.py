# Owner: agent-platform
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentEventSource(Base):
    __tablename__ = "agent_event_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # internal, webhook, cron, etc
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class AgentEventTrigger(Base):
    __tablename__ = "agent_event_triggers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_event_sources.id", ondelete="SET NULL"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)  # on_schedule, on_webhook, on_message_queue, etc
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    filter_expression: Mapped[str | None] = mapped_column(Text, nullable=True) # JSONPath or simple expression
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    agent = relationship("AgentDefinition")
    source = relationship("AgentEventSource")

class AgentEventDelivery(Base):
    __tablename__ = "agent_event_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_event_triggers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending, delivered, failed, dlq
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dlq_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    trigger = relationship("AgentEventTrigger")
    run = relationship("AgentRun")

class AgentEventDedupKey(Base):
    __tablename__ = "agent_event_dedup_keys"

    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class AgentEventSubscription(Base):
    __tablename__ = "agent_event_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False)

    agent = relationship("AgentDefinition")

class AgentScheduledTrigger(Base):
    __tablename__ = "agent_scheduled_triggers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_event_triggers.id", ondelete="CASCADE"), nullable=False, unique=True)
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    trigger = relationship("AgentEventTrigger")

class AgentWebhookTrigger(Base):
    __tablename__ = "agent_webhook_triggers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_event_triggers.id", ondelete="CASCADE"), nullable=False, unique=True)
    secret_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    signature_header: Mapped[str] = mapped_column(String(128), default="X-Agent-Signature")

    trigger = relationship("AgentEventTrigger")
