import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    contact_phone: str | None = None
    segment: str
    status: str = "new"
    source: str
    notes: str | None = None
    estimated_value: float = 0.0
    next_follow_up_at: datetime | None = None
    is_demo: bool = False


class SalesLeadCreate(SalesLeadBase):
    pass


class SalesLeadUpdate(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    segment: str | None = None
    status: str | None = None
    source: str | None = None
    notes: str | None = None
    estimated_value: float | None = None
    next_follow_up_at: datetime | None = None


class SalesLead(SalesLeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    timeline_notes: list[SalesLeadNote] = []


class LeadAdvanceStage(BaseModel):
    new_status: str
    note: str | None = None


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
