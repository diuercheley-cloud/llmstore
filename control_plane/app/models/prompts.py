# Owner: agent-platform
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    variable_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict) # JSON Schema for variables
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions = relationship("PromptTemplateVersion", back_populates="template", cascade="all, delete-orphan")
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id", use_alter=True), nullable=True)

class PromptTemplateVersion(Base):
    __tablename__ = "prompt_template_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False) # e.g. "v1", "2024-05-30.1"
    content: Mapped[str] = mapped_column(Text, nullable=False) # The actual prompt text with {{vars}}
    provider_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict) # temperature, model, etc.
    status: Mapped[str] = mapped_column(String(32), default="draft") # draft, staging, production, archived
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    template = relationship("PromptTemplate", foreign_keys=[template_id], back_populates="versions")

class PromptExperiment(Base):
    __tablename__ = "prompt_experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False)
    version_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id"), nullable=False)
    version_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running") # running, completed
    traffic_split: Mapped[float] = mapped_column(Float, default=0.5) # 0.5 = 50/50
    winner_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class PromptPlaygroundRun(Base):
    __tablename__ = "prompt_playground_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_template_versions.id", ondelete="CASCADE"), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
