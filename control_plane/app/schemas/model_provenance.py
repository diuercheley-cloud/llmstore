import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ModelProvenanceRead(BaseModel):
    id: uuid.UUID
    model_id: str
    source: str
    license: str | None
    weights_hash: str | None
    tokenizer_hash: str | None
    config_hash: str | None
    signature_status: str
    created_at: datetime
    verified_at: datetime | None


class WatermarkVerificationRequest(BaseModel):
    text: str
    watermark_id: str | None = None


class WatermarkVerificationResponse(BaseModel):
    is_authentic: bool
    confidence: float
    metadata: dict[str, Any]
    detected_id: str | None
