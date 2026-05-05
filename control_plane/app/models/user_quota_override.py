import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.core.time import utc_now

class UserQuotaOverride(Base):
    __tablename__ = "user_quota_overrides"

    user_id = Column(UUID(as_uuid=True), primary_key=True) # Usually the client.id
    daily_quota_override = Column(Integer, nullable=True)
    monthly_quota_override = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    updated_by_role = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
