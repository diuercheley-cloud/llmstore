from typing import List, Optional
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
    rotation_due_at: Optional[datetime]
    created_at: datetime
    rotated_at: Optional[datetime]


class EncryptionKeyCreate(BaseModel):
    client_id: uuid.UUID
    purpose: str = "general"

class EncryptRequest(BaseModel):
    client_id: uuid.UUID
    payload: str
    artifact_type: str
    resource_type: str
    resource_id: Optional[str] = None
    key_purpose: str = "general"

class EncryptedArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: Optional[uuid.UUID]
    artifact_type: str
    resource_type: str
    resource_id: Optional[str]
    encryption_mode: str
    encrypted_payload: str
    payload_hash: str
    key_id: Optional[uuid.UUID]
    created_at: datetime


class DecryptRequest(BaseModel):
    artifact_id: uuid.UUID

class DecryptResponse(BaseModel):
    payload: str

class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: Optional[uuid.UUID]
    event_type: str
    resource_type: str
    resource_id: Optional[str]
    key_fingerprint: Optional[str]
    success: bool
    created_at: datetime


class ClassificationRequest(BaseModel):
    payload: str

class ClassificationResponse(BaseModel):
    classification: str
