# Owner: agent-platform
import asyncio
import logging
import uuid
from typing import Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.payments import PaymentAuditEvent, PaymentCustomer, PaymentIntent
from app.services.billing.payments.mock_payment_provider import MockPaymentProvider
from app.services.billing.payments.payment_provider import PaymentProvider
from app.services.billing.payments.stripe_provider import StripePaymentProvider
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("invoice_payment")

# Global lock to prevent race conditions during customer creation in same process
_customer_lock = asyncio.Lock()

def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    if settings.payment_provider == "stripe":
        return StripePaymentProvider()
    return MockPaymentProvider()

async def get_or_create_customer(
    db: AsyncSession,
    client_id: uuid.UUID,
    provider_name: str,
    provider: PaymentProvider
) -> str:
    async with _customer_lock:
        # 1. Fetch Client name/email
        stmt_client = select(Client).where(Client.id == client_id)
        res_client = await db.execute(stmt_client)
        client = res_client.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found.")

        # 2. Check if customer already exists for this provider
        stmt_cust = select(PaymentCustomer).where(
            PaymentCustomer.client_id == client_id,
            PaymentCustomer.provider == provider_name
        )
        res_cust = await db.execute(stmt_cust)
        cust = res_cust.scalar_one_or_none()
        if cust:
            return cust.provider_customer_id

        # 3. Create on provider
        email = f"billing-{client_id}@example.com"
        cust_id = await provider.create_customer(client_id, client.name, email)

        # 4. Save in DB
        cust = PaymentCustomer(
            id=uuid.uuid4(),
            client_id=client_id,
            provider=provider_name,
            provider_customer_id=cust_id
        )
        db.add(cust)
        await db.commit() # Commit here to release for other requests
        
        return cust_id


class PaymentService:
    @staticmethod
    async def create_payment_intent(
        db: AsyncSession,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str = "BRL",
        invoice_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        idempotency_key: Optional[str] = None
    ) -> PaymentIntent:
        # Check idempotency
        if idempotency_key:
            stmt = select(PaymentIntent).where(PaymentIntent.idempotency_key == idempotency_key)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                logger.info(f"Returning existing payment intent due to idempotency match: {existing.id}")
                return existing

        provider = get_payment_provider()
        provider_name = get_settings().payment_provider

        # 1. Get or create customer ID for provider
        provider_cust_id = await get_or_create_customer(db, client_id, provider_name, provider)

        # 2. Create intent on provider
        external_res = await provider.create_payment_intent(
            client_id=client_id,
            amount_cents=amount_cents,
            currency=currency,
            provider_customer_id=provider_cust_id,
            idempotency_key=idempotency_key
        )

        # 3. Save intent in DB
        amount_brl = amount_cents / 100.0
        intent = PaymentIntent(
            id=uuid.uuid4(),
            client_id=client_id,
            invoice_id=invoice_id,
            provider=provider_name,
            provider_intent_id=external_res["id"],
            client_secret=external_res.get("client_secret"),
            amount_cents=amount_cents,
            currency=currency.lower(),
            status=external_res.get("status", "requires_payment_method"),
            idempotency_key=idempotency_key
        )
        db.add(intent)
        
        # 4. Log event
        event = PaymentAuditEvent(
            id=uuid.uuid4(),
            client_id=client_id,
            event_type="payment.intent_created",
            status="success",
            provider=provider_name,
            metadata_json={
                "intent_id": str(intent.id),
                "external_id": external_res["id"],
                "amount_cents": amount_cents
            }
        )
        db.add(event)
        
        await db.commit()
        await db.refresh(intent)
        return intent

    @staticmethod
    async def reconcile_payment_intent(db: AsyncSession, intent_id: uuid.UUID) -> PaymentIntent:
        stmt = select(PaymentIntent).where(PaymentIntent.id == intent_id)
        res = await db.execute(stmt)
        intent = res.scalar_one_or_none()
        if not intent:
            raise HTTPException(status_code=404, detail="Payment intent not found.")
            
        # In a real system we'd call provider API here.
        # For now we just return it.
        return intent

    @staticmethod
    async def confirm_payment(db: AsyncSession, intent_id: uuid.UUID) -> PaymentIntent:
        stmt = select(PaymentIntent).where(PaymentIntent.id == intent_id)
        res = await db.execute(stmt)
        intent = res.scalar_one_or_none()
        if not intent:
            raise HTTPException(status_code=404, detail="Payment intent not found.")

        # Update status (in a real system we'd check provider API)
        intent.status = "succeeded"
        intent.updated_at = utc_now()
        
        event = PaymentAuditEvent(
            id=uuid.uuid4(),
            client_id=intent.client_id,
            event_type="payment.succeeded",
            status="success",
            provider=intent.provider,
            metadata_json={"intent_id": str(intent.id)}
        )
        db.add(event)
        
        await db.commit()
        await db.refresh(intent)
        return intent

    @staticmethod
    async def list_client_payments(db: AsyncSession, client_id: uuid.UUID) -> list[PaymentIntent]:
        stmt = select(PaymentIntent).where(PaymentIntent.client_id == client_id).order_by(PaymentIntent.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_audit_log(db: AsyncSession, client_id: uuid.UUID) -> list[PaymentAuditEvent]:
        stmt = select(PaymentAuditEvent).where(PaymentAuditEvent.client_id == client_id).order_by(PaymentAuditEvent.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())
