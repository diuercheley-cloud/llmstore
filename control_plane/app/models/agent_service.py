# Owner: agent-platform
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentServiceTier(Base):
    __tablename__ = "agent_service_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False) # free, pro, enterprise
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=10)
    monthly_run_limit: Mapped[int] = mapped_column(Integer, default=1000)
    price_per_run_brl: Mapped[float] = mapped_column(Float, default=0.0)
    price_per_1k_tokens_brl: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_fee_brl: Mapped[float] = mapped_column(Float, default=0.0)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class AgentServiceUsage(Base):
    __tablename__ = "agent_service_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    tier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_service_tiers.id"), nullable=False)
    
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimated_brl: Mapped[float] = mapped_column(Float, default=0.0)
    invocation_mode: Mapped[str] = mapped_column(String(16), default="async") # sync, async
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    tier = relationship("AgentServiceTier")

class AgentCallbackWebhook(Base):
    __tablename__ = "agent_callback_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key: Mapped[str] = mapped_column(String(256), nullable=False) # Used for HMAC signatures
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
