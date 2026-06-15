import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BillingDisputeOpen(BaseModel):
    dispute_type: str
    # qos_usage|wallet_debit|invoice_amount|priority_charge|other
    claimed_amount_brl: Decimal
    disputed_reason: str
    qos_billing_record_id: uuid.UUID | None = None
    invoice_id: uuid.UUID | None = None
    wallet_transaction_id: uuid.UUID | None = None


class BillingDisputeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    dispute_type: str
    status: str
    claimed_amount_brl: Decimal
    disputed_reason: str
    admin_notes: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
