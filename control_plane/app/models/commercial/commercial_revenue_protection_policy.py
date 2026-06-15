import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialRevenueProtectionPolicy(Base):
    __tablename__ = "commercial_revenue_protection_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity_threshold: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    action_type: Mapped[str] = mapped_column(String(48), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="report_only")
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    actions = relationship("CommercialRevenueProtectionAction", back_populates="policy")
