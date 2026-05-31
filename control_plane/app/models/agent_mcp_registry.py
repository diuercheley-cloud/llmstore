import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class AgentMCPServer(Base):
    __tablename__ = "agent_mcp_servers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_agent_mcp_servers_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    transport: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(1024), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(64), nullable=False, default="untrusted")
    approved_tools: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    discovered_tools: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    discovered_resources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    discovered_prompts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    server_info: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
