from typing import Any
import uuid

from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.core.time import utc_now


class AdminActionLog(Base):
    __tablename__ = "admin_actions_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(100), nullable=False)
    admin_role = Column(String(50), nullable=False)
    target_user_id = Column(String(50), nullable=True)
    request_path = Column(String(255), nullable=True)
    request_method = Column(String(20), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    payload_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
