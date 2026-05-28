from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class CommercialRoutingEvent(Base):
    __tablename__ = "commercial_routing_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    endpoint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_requested: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    selected_provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    selected_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_is_cloud: Mapped[bool] = mapped_column(Boolean, default=False)
    
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Estimated financials
    estimated_cost_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    estimated_revenue_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    estimated_margin_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    estimated_margin_percent: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    
    # Actual financials (to be updated later)
    actual_cost_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_revenue_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_margin_brl: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    actual_margin_percent: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    
    selected_score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    
    # Detailed routing data (JSON)
    ranked_routes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rejected_routes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    guardrail_decisions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Phase 9: Config Tracking
    commercial_config_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    commercial_config_variant: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True) # stable|canary|default

    # Phase 20: SLA/QoS Tracking
    qos_tier: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sla_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    degradation_applied: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qos_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)

    client = relationship("Client")
