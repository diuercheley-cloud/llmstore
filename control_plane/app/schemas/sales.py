import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class SalesLeadNoteBase(BaseModel):
    content: str

class SalesLeadNoteCreate(SalesLeadNoteBase):
    pass

class SalesLeadNote(SalesLeadNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    created_at: datetime

class SalesLeadBase(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    segment: str
    status: str = "new"
    source: str
    notes: Optional[str] = None
    estimated_value: float = 0.0
    next_follow_up_at: Optional[datetime] = None
    is_demo: bool = False

class SalesLeadCreate(SalesLeadBase):
    pass

class SalesLeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    segment: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    estimated_value: Optional[float] = None
    next_follow_up_at: Optional[datetime] = None

class SalesLead(SalesLeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    timeline_notes: List[SalesLeadNote] = []

class LeadAdvanceStage(BaseModel):
    new_status: str
    note: Optional[str] = None

class QuotePreviewRequest(BaseModel):
    company_name: str
    plan: str
    users: int = 0
    models: int = 1
    rag: bool = False
    tts: bool = False
    embeddings: bool = False
    responses: int = 0
    support_hours: int = 0
    custom_integration_hours: int = 0
    discount_percent: float = 0.0

class QuotePreviewResponse(BaseModel):
    company_name: str
    plan: str
    currency: str
    details: dict
    totals: dict
    validity_days: int
    timestamp: str
