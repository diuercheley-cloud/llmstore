import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EncryptionKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    key_version: str
    key_purpose: str
    key_status: str
    key_fingerprint: str
    rotation_due_at: datetime | None
    created_at: datetime
    rotated_at: datetime | None


class EncryptionKeyCreate(BaseModel):
    client_id: uuid.UUID
    purpose: str = "general"


class EncryptRequest(BaseModel):
    client_id: uuid.UUID
    payload: str
    artifact_type: str
    resource_type: str
    resource_id: str | None = None
    key_purpose: str = "general"


class EncryptedArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID | None
    artifact_type: str
    resource_type: str
    resource_id: str | None
    encryption_mode: str
    encrypted_payload: str
    payload_hash: str
    key_id: uuid.UUID | None
    created_at: datetime


class DecryptRequest(BaseModel):
    artifact_id: uuid.UUID


class DecryptResponse(BaseModel):
    payload: str


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID | None
    event_type: str
    resource_type: str
    resource_id: str | None
    key_fingerprint: str | None
    success: bool
    created_at: datetime


class ClassificationRequest(BaseModel):
    payload: str


class ClassificationResponse(BaseModel):
    classification: str
