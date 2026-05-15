import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel


class BillingDisputeOpen(BaseModel):
    dispute_type: str
    # qos_usage|wallet_debit|invoice_amount|priority_charge|other
    claimed_amount_brl: Decimal
    disputed_reason: str
    qos_billing_record_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None
    wallet_transaction_id: Optional[uuid.UUID] = None


class BillingDisputeRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    dispute_type: str
    status: str
    claimed_amount_brl: Decimal
    disputed_reason: str
    admin_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
