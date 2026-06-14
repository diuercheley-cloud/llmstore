import uuid
from datetime import datetime, timezone

from app.db.base import Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID


class GlobalRoutingPolicyVersion(Base):
    __tablename__ = "global_routing_policy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, nullable=False)
    policy_json = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(32), nullable=False, default="draft")  # draft, active, rolled_back
    previous_version_id = Column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<GlobalRoutingPolicyVersion(id={self.id}, version={self.version}, status={self.status})>"
