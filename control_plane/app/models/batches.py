# Owner: agent-platform
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="validating")  # validating, in_progress, completed, failed, cancelled
    input_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    output_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    error_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    budget_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items = relationship("BatchJobItem", back_populates="batch", cascade="all, delete-orphan")

class BatchJobItem(Base):
    __tablename__ = "batch_job_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    custom_id: Mapped[str | None] = mapped_column(String(256), nullable=True) # User provided ID for tracking
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, in_progress, completed, failed
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    batch = relationship("BatchJob", back_populates="items")
