import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    tenant_id: Optional[str] = "default"

class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tenant_id: str
    description: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime

class ArtifactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    artifact_type: str
    content: str
    creator_id: str
    creator_type: str = "human" # human|agent
    run_id: Optional[uuid.UUID] = None
    step_id: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None
    version_metadata: Optional[Dict[str, Any]] = None

class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    tenant_id: str
    name: str
    artifact_type: str
    current_version_id: Optional[uuid.UUID]
    owner_id: str
    status: str
    created_at: datetime
    updated_at: datetime

class ArtifactVersionCreate(BaseModel):
    content: str
    creator_id: str
    creator_type: str = "human"
    run_id: Optional[uuid.UUID] = None
    step_id: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None
    version_metadata: Optional[Dict[str, Any]] = None
    expected_version_id: Optional[uuid.UUID] = None # For optimistic locking

class ArtifactVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_number: int
    content: str
    content_hash: str
    creator_id: str
    creator_type: str
    run_id: Optional[uuid.UUID]
    step_id: Optional[uuid.UUID]
    change_summary: Optional[str]
    version_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

class ArtifactLockAcquire(BaseModel):
    holder_id: str
    holder_type: str = "human" # human|agent
    lock_type: Optional[str] = "exclusive"
    expires_in_seconds: Optional[int] = 300

class ArtifactLockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    holder_id: str
    holder_type: str
    lock_type: str
    expires_at: Optional[datetime]
    created_at: datetime

class ArtifactReviewCreate(BaseModel):
    version_id: uuid.UUID
    reviewer_id: str
    reviewer_type: str = "human"
    status: str # pending|approved|rejected|changes_requested
    comment: Optional[str] = None

class ArtifactReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_id: uuid.UUID
    reviewer_id: str
    reviewer_type: str
    status: str
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

class ArtifactCommentCreate(BaseModel):
    content: str
    author_id: str
    author_type: str = "human"
    version_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None

class ArtifactCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    version_id: Optional[uuid.UUID]
    author_id: str
    author_type: str
    content: str
    parent_id: Optional[uuid.UUID]
    created_at: datetime

class ArtifactEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    artifact_id: uuid.UUID
    event_type: str
    actor_id: str
    actor_type: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime

class DiffStructuredLine(BaseModel):
    type: str # equal|delete|insert
    value: str

class ArtifactDiffResponse(BaseModel):
    raw_diff: str
    structured: List[DiffStructuredLine]
