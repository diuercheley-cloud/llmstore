import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentExecutionJob(Base):
    # Owner: agent-platform
    __tablename__ = "agent_execution_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    queue_status: Mapped[str] = mapped_column(
        String(32), default="queued", index=True
    )  # queued|leased|running|waiting_approval|completed|failed|cancelled|dead_letter

    # Durable Queue Extensions
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(256), unique=True, nullable=True, index=True
    )
    deduplication_key: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    backoff_factor: Mapped[float] = mapped_column(Float, default=2.0)
    initial_delay_seconds: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    agent_run = relationship("AgentRun")
    lease = relationship(
        "AgentExecutionLease", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    retries = relationship(
        "AgentExecutionRetry", back_populates="job", cascade="all, delete-orphan"
    )


class AgentWorkerHeartbeat(Base):
    # Owner: agent-platform
    __tablename__ = "agent_worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AgentExecutionLease(Base):
    # Owner: agent-platform
    __tablename__ = "agent_execution_leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_execution_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    worker_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    leased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    job = relationship("AgentExecutionJob", back_populates="lease")


class AgentExecutionRetry(Base):
    # Owner: agent-platform
    __tablename__ = "agent_execution_retries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_execution_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("AgentExecutionJob", back_populates="retries")


class AgentExecutionDeadLetter(Base):
    # Owner: agent-platform
    __tablename__ = "agent_execution_dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dlq_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
