# Owner: agent-platform
import uuid
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.client import Client
from app.models.billing_invoice import BillingInvoice
from app.models.payments import PaymentCustomer, PaymentIntent, PaymentAuditEvent
from app.services.billing.payments.payment_provider import PaymentProvider
from app.services.billing.payments.mock_payment_provider import MockPaymentProvider
from app.services.billing.payments.stripe_payment_provider import StripePaymentProvider

logger = logging.getLogger("invoice_payment")

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
    await db.flush()
    return cust_id


class PaymentService:
    @staticmethod
    async def create_payment_intent(
        db: AsyncSession,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        invoice_id: Optional[uuid.UUID] = None,
        idempotency_key: Optional[str] = None
    ) -> PaymentIntent:
        # Verify payment processing enabled
        settings = get_settings()
        if not settings.payment_processing_enabled:
            raise HTTPException(status_code=403, detail="Payment processing is disabled.")

        # Idempotency check
        if idempotency_key:
            stmt = select(PaymentIntent).where(
                PaymentIntent.client_id == client_id,
                PaymentIntent.idempotency_key == idempotency_key
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                logger.info(f"Returning existing payment intent due to idempotency match: {existing.id}")
                return existing

        provider_name = settings.payment_provider
        provider = get_payment_provider()

        # Get customer ID
        provider_cust_id = await get_or_create_customer(db, client_id, provider_name, provider)

        # Create intent on provider
        intent_details = await provider.create_payment_intent(
            client_id=client_id,
            amount_cents=amount_cents,
            currency=currency,
            provider_customer_id=provider_cust_id,
            idempotency_key=idempotency_key
        )

        # Save PaymentIntent in DB
        intent = PaymentIntent(
            id=uuid.uuid4(),
            client_id=client_id,
            invoice_id=invoice_id,
            amount_cents=amount_cents,
            currency=currency.lower(),
            status=intent_details["status"],
            provider=provider_name,
            provider_intent_id=intent_details["id"],
            client_secret=intent_details["client_secret"],
            idempotency_key=idempotency_key
        )
        db.add(intent)

        # Audit event - NEVER LOG card or token or client_secret
        audit = PaymentAuditEvent(
            id=uuid.uuid4(),
            client_id=client_id,
            event_type="payment.intent_created",
            status="success",
            provider=provider_name,
            actor_identifier="system",
            metadata_json={
                "amount_cents": amount_cents,
                "currency": currency,
                "provider_intent_id": intent_details["id"],
                "idempotency_key": idempotency_key
            }
        )
        db.add(audit)
        await db.commit()
        await db.refresh(intent)
        return intent

    @staticmethod
    async def reconcile_payment_intent(
        db: AsyncSession,
        intent_id: uuid.UUID
    ) -> PaymentIntent:
        # Load from DB
        stmt = select(PaymentIntent).where(PaymentIntent.id == intent_id)
        res = await db.execute(stmt)
        intent = res.scalar_one_or_none()
        if not intent:
            raise HTTPException(status_code=404, detail="Payment intent not found.")

        provider = get_payment_provider()
        # Retrieve freshest status from provider
        details = await provider.retrieve_payment_intent(intent.provider_intent_id)

        old_status = intent.status
        new_status = details["status"]

        if old_status != new_status:
            intent.status = new_status
            intent.updated_at = utc_now()

            # Record audit
            audit = PaymentAuditEvent(
                id=uuid.uuid4(),
                client_id=intent.client_id,
                event_type="payment.reconciled",
                status="success",
                provider=intent.provider,
                actor_identifier="system",
                metadata_json={
                    "provider_intent_id": intent.provider_intent_id,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
            db.add(audit)

            # If succeeded, reconcile with invoice if linked
            if new_status == "succeeded" and intent.invoice_id:
                stmt_inv = select(BillingInvoice).where(BillingInvoice.id == intent.invoice_id)
                res_inv = await db.execute(stmt_inv)
                invoice = res_inv.scalar_one_or_none()
                if invoice:
                    invoice.status = "paid"
                    invoice.updated_at = utc_now()

            await db.commit()
            await db.refresh(intent)

        return intent
