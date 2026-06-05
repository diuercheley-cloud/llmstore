import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ModelProvenanceRead(BaseModel):
    id: uuid.UUID
    model_id: str
    source: str
    license: Optional[str]
    weights_hash: Optional[str]
    tokenizer_hash: Optional[str]
    config_hash: Optional[str]
    signature_status: str
    created_at: datetime
    verified_at: Optional[datetime]


class WatermarkVerificationRequest(BaseModel):
    text: str
    watermark_id: Optional[str] = None


class WatermarkVerificationResponse(BaseModel):
    is_authentic: bool
    confidence: float
    metadata: Dict[str, Any]
    detected_id: Optional[str]
