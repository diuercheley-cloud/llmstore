import uuid
from datetime import datetime
from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class AgentDLPViolation(Base):
    __tablename__ = "agent_dlp_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)  # ingress | egress
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)  # prompt | response | tool_input | tool_output
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of findings: [{"type": "...", "value": "...", "start": X, "end": Y}]
    action_taken: Mapped[str] = mapped_column(String(32), default="redacted")  # redacted | blocked | allowed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
