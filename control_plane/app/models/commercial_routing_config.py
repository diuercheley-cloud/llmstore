from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from app.db.base import Base
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID


class CommercialRoutingConfig(Base):
    __tablename__ = "commercial_routing_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # scope_type: global|provider|model|provider_model
    scope_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(100), nullable=True, index=True)
    model = Column(String(100), nullable=True, index=True)
    
    cost_multiplier = Column(Float, nullable=False, default=1.0)
    margin_weight = Column(Float, nullable=False, default=0.6)
    latency_weight = Column(Float, nullable=False, default=0.2)
    quality_weight = Column(Float, nullable=False, default=0.2)
    local_route_bonus = Column(Float, nullable=False, default=20.0)
    min_margin_percent = Column(Float, nullable=False, default=10.0)
    
    # source: default|manual|calibration
    source = Column(String(50), nullable=False, default="manual")
    
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Phase 8: Auto Apply & Canary
    canary_percent = Column(sa.Integer, nullable=False, default=0)
    canary_enabled = Column(Boolean, nullable=False, default=False, index=True)
    
    auto_applied = Column(Boolean, nullable=False, default=False, index=True)
    can_auto_apply = Column(Boolean, nullable=False, default=False)
    
    auto_apply_reason = Column(String(255), nullable=True)
    auto_apply_source_event_count = Column(sa.Integer, nullable=True)
    auto_apply_confidence = Column(String(50), nullable=True)
    
    promoted_from_config_id = Column(UUID(as_uuid=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Phase 9: Canary Auto Promotion
    canary_started_at = Column(DateTime(timezone=True), nullable=True)
    canary_last_promoted_at = Column(DateTime(timezone=True), nullable=True)
    canary_current_step = Column(sa.Integer, nullable=True)
    canary_target_step = Column(sa.Integer, nullable=True)
    canary_observation_window_minutes = Column(sa.Integer, nullable=True)
    
    # pending|observing|promoted|rolled_back|failed|completed
    canary_promotion_status = Column(String(50), nullable=True, index=True)
    canary_failure_reason = Column(Text, nullable=True)
    stable_promoted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        sa.Index("ix_commercial_routing_config_canary_lookup", "provider", "model", "canary_enabled"),
    )

    def __repr__(self) -> str:
        return f"<CommercialRoutingConfig(id={self.id}, scope={self.scope_type}, active={self.is_active})>"
