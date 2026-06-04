# Owner: agent-platform
import uuid
from typing import Any, Optional

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.auth import require_client
from app.services.billing.payments.invoice_payment import PaymentService
from app.services.billing.payments.payment_webhooks import PaymentWebhookService
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["billing-payments"])

class CreatePaymentIntentRequest(BaseModel):
    client_id: uuid.UUID
    amount_cents: int
    currency: str = "brl"
    invoice_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = None

class PaymentIntentResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: Optional[uuid.UUID]
    amount_cents: int
    currency: str
    status: str
    provider: str
    provider_intent_id: str
    client_secret: Optional[str]
    idempotency_key: Optional[str]
    created_at: str
    updated_at: str

def to_intent_response(intent) -> PaymentIntentResponse:
    return PaymentIntentResponse(
        id=intent.id,
        client_id=intent.client_id,
        invoice_id=intent.invoice_id,
        amount_cents=intent.amount_cents,
        currency=intent.currency,
        status=intent.status,
        provider=intent.provider,
        provider_intent_id=intent.provider_intent_id,
        client_secret=intent.client_secret,
        idempotency_key=intent.idempotency_key,
        created_at=intent.created_at.isoformat() if intent.created_at else "",
        updated_at=intent.updated_at.isoformat() if intent.updated_at else ""
    )

@router.post("/admin/billing/payments/create-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    req: CreatePaymentIntentRequest,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
):
    settings = get_settings()
    if not settings.payment_processing_enabled:
        raise HTTPException(status_code=403, detail="Payment processing is disabled.")

    intent = await PaymentService.create_payment_intent(
        db=db,
        client_id=req.client_id,
        amount_cents=req.amount_cents,
        currency=req.currency,
        invoice_id=req.invoice_id,
        idempotency_key=req.idempotency_key
    )
    return to_intent_response(intent)

@router.post("/billing/webhooks/stripe")
async def stripe_payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    settings = get_settings()
    if not settings.stripe_payment_enabled:
        raise HTTPException(status_code=403, detail="Stripe payment is disabled.")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    payload = await request.body()
    return await PaymentWebhookService.process_stripe_webhook(
        db=db,
        payload_bytes=payload,
        signature_header=stripe_signature
    )

class CreatePixPaymentRequest(BaseModel):
    amount_cents: int
    idempotency_key: Optional[str] = None

class CreateCardPaymentRequest(BaseModel):
    amount_cents: int
    payment_method_id: str
    idempotency_key: Optional[str] = None

@router.post("/billing/payments/pix")
async def create_pix_payment(
    req: CreatePixPaymentRequest,
    db: AsyncSession = Depends(get_db_session),
    client: Any = Depends(require_client)
):
    from app.services.billing.payments.pix_service import PixService
    return await PixService.create_payment(db, client.id, req.amount_cents, req.idempotency_key)

@router.post("/billing/payments/card")
async def create_card_payment(
    req: CreateCardPaymentRequest,
    db: AsyncSession = Depends(get_db_session),
    client: Any = Depends(require_client)
):
    from app.services.billing.payments.card_service import CardService
    return await CardService.create_payment(db, client.id, req.amount_cents, req.payment_method_id, req.idempotency_key)

@router.post("/billing/webhooks/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    x_signature: Optional[str] = Header(None, alias="X-Payment-Signature")
):
    from app.services.billing.payments.payment_reconciliation import PaymentReconciliationService
    payload = await request.body()
    success = await PaymentReconciliationService.process_webhook(db, provider, payload, x_signature or "")
    if not success:
        raise HTTPException(status_code=400, detail="Webhook validation failed")
    return {"status": "ok"}

@router.get("/admin/billing/payments/{id}", response_model=PaymentIntentResponse)
async def get_payment_intent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
):
    settings = get_settings()
    if not settings.payment_processing_enabled:
        raise HTTPException(status_code=403, detail="Payment processing is disabled.")

    # Reconcile status with provider and return
    intent = await PaymentService.reconcile_payment_intent(db, id)
    return to_intent_response(intent)
