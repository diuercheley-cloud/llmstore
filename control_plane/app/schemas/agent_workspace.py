import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    tenant_id: str | None = "default"


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tenant_id: str
    description: str | None
    owner_id: str
    created_at: datetime
    updated_at: datetime


class ArtifactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    artifact_type: str
    content: str
    creator_id: str
    creator_type: str = "human"  # human|agent
    run_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    change_summary: str | None = None
    version_metadata: dict[str, Any] | None = None


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    tenant_id: str
    name: str
    artifact_type: str
    current_version_id: uuid.UUID | None
    owner_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class ArtifactVersionCreate(BaseModel):
    content: str
    creator_id: str
    creator_type: str = "human"
    run_id: uuid.UUID | None = None
    step_id: uuid.UUID | None = None
    change_summary: str | None = None
    version_metadata: dict[str, Any] | None = None
    expected_version_id: uuid.UUID | None = None  # For optimistic locking


class ArtifactVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_number: int
    content: str
    content_hash: str
    creator_id: str
    creator_type: str
    run_id: uuid.UUID | None
    step_id: uuid.UUID | None
    change_summary: str | None
    version_metadata: dict[str, Any] | None = None
    created_at: datetime


class ArtifactLockAcquire(BaseModel):
    holder_id: str
    holder_type: str = "human"  # human|agent
    lock_type: str | None = "exclusive"
    expires_in_seconds: int | None = 300


class ArtifactLockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    holder_id: str
    holder_type: str
    lock_type: str
    expires_at: datetime | None
    created_at: datetime


class ArtifactReviewCreate(BaseModel):
    version_id: uuid.UUID
    reviewer_id: str
    reviewer_type: str = "human"
    status: str  # pending|approved|rejected|changes_requested
    comment: str | None = None


class ArtifactReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_id: uuid.UUID
    reviewer_id: str
    reviewer_type: str
    status: str
    comment: str | None
    created_at: datetime
    updated_at: datetime


class ArtifactCommentCreate(BaseModel):
    content: str
    author_id: str
    author_type: str = "human"
    version_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None


class ArtifactCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_id: uuid.UUID | None
    author_id: str
    author_type: str
    content: str
    parent_id: uuid.UUID | None
    created_at: datetime


class ArtifactEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    event_type: str
    actor_id: str
    actor_type: str
    payload: dict[str, Any] | None
    created_at: datetime


class DiffStructuredLine(BaseModel):
    type: str  # equal|delete|insert
    value: str


class ArtifactDiffResponse(BaseModel):
    raw_diff: str
    structured: list[DiffStructuredLine]
