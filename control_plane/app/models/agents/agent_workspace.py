import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentWorkspace(Base):
    # Owner: agent-platform
    __tablename__ = "agent_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    artifacts = relationship(
        "AgentSharedArtifact", back_populates="workspace", cascade="all, delete-orphan"
    )


class AgentSharedArtifact(Base):
    # Owner: agent-platform
    __tablename__ = "agent_shared_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # markdown_doc|code_file|json_plan|...
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="draft"
    )  # draft|review|published|deprecated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    workspace = relationship("AgentWorkspace", back_populates="artifacts")
    versions = relationship(
        "AgentArtifactVersion", back_populates="artifact", cascade="all, delete-orphan"
    )
    lock = relationship(
        "AgentArtifactLock", back_populates="artifact", uselist=False, cascade="all, delete-orphan"
    )
    reviews = relationship(
        "AgentArtifactReview", back_populates="artifact", cascade="all, delete-orphan"
    )
    comments = relationship(
        "AgentArtifactComment", back_populates="artifact", cascade="all, delete-orphan"
    )


class AgentArtifactVersion(Base):
    # Owner: agent-platform
    __tablename__ = "agent_artifact_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shared_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    creator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    creator_type: Mapped[str] = mapped_column(String(32), nullable=False)  # human|agent
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    artifact = relationship("AgentSharedArtifact", back_populates="versions")


class AgentArtifactLock(Base):
    # Owner: agent-platform
    __tablename__ = "agent_artifact_locks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shared_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    holder_id: Mapped[str] = mapped_column(String(128), nullable=False)
    holder_type: Mapped[str] = mapped_column(String(32), nullable=False)  # human|agent
    lock_type: Mapped[str] = mapped_column(String(32), default="exclusive")  # exclusive|shared
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    artifact = relationship("AgentSharedArtifact", back_populates="lock")


class AgentArtifactReview(Base):
    # Owner: agent-platform
    __tablename__ = "agent_artifact_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shared_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_artifact_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_type: Mapped[str] = mapped_column(String(32), nullable=False)  # human|agent
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pending|approved|rejected|changes_requested
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    artifact = relationship("AgentSharedArtifact", back_populates="reviews")


class AgentArtifactComment(Base):
    # Owner: agent-platform
    __tablename__ = "agent_artifact_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shared_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_artifact_versions.id", ondelete="CASCADE"),
        nullable=True,
    )
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_type: Mapped[str] = mapped_column(String(32), nullable=False)  # human|agent
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_artifact_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    artifact = relationship("AgentSharedArtifact", back_populates="comments")


class AgentArtifactEvent(Base):
    # Owner: agent-platform
    __tablename__ = "agent_artifact_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_shared_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # created|updated|locked|unlocked|reviewed|commented
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
