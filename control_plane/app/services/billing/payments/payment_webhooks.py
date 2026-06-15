# Owner: agent-platform
import json
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing.billing_invoice import BillingInvoice
from app.models.billing.payments import (
    PaymentAuditEvent,
    PaymentIntent,
    PaymentProcessingWebhookEvent,
)
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("payment_webhooks")


class PaymentWebhookService:
    @staticmethod
    async def process_stripe_webhook(
        db: AsyncSession, payload_bytes: bytes, signature_header: str
    ) -> dict[str, Any]:
        settings = get_settings()
        if not settings.stripe_payment_enabled:
            raise HTTPException(status_code=403, detail="Stripe payment is disabled.")

        # 1. Verify webhook signature
        import stripe

        stripe.api_key = settings.stripe_secret_key
        try:
            event = stripe.Webhook.construct_event(
                payload_bytes, signature_header, settings.stripe_webhook_secret
            )
        except Exception as e:
            logger.warning(f"Stripe Webhook signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

        # 2. Check duplicate / Idempotency check
        provider_event_id = event["id"]
        stmt_dup = select(PaymentProcessingWebhookEvent).where(
            PaymentProcessingWebhookEvent.provider_event_id == provider_event_id,
            PaymentProcessingWebhookEvent.provider == "stripe",
        )
        res_dup = await db.execute(stmt_dup)
        existing = res_dup.scalar_one_or_none()
        if existing:
            logger.info(
                f"Duplicate Stripe webhook received, skipping processing. Event ID: {provider_event_id}"
            )
            return {"status": "idempotent_skip", "event_id": provider_event_id}

        # Save webhook event as pending in DB
        webhook_event = PaymentProcessingWebhookEvent(
            id=uuid.uuid4(),
            provider="stripe",
            provider_event_id=provider_event_id,
            event_type=event["type"],
            payload_json=json.dumps(event),
            status="pending",
        )
        db.add(webhook_event)
        await db.flush()

        # 3. Process event types
        event_type = event["type"]
        event_data = event["data"]["object"]
        provider_intent_id = event_data.get("id")

        if event_type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
            # Reconcile PaymentIntent in DB
            stmt_intent = select(PaymentIntent).where(
                PaymentIntent.provider_intent_id == provider_intent_id,
                PaymentIntent.provider == "stripe",
            )
            res_intent = await db.execute(stmt_intent)
            intent = res_intent.scalar_one_or_none()

            if intent:
                new_status = "succeeded" if event_type == "payment_intent.succeeded" else "failed"
                old_status = intent.status
                intent.status = new_status
                intent.updated_at = utc_now()

                # Reconcile invoice if status succeeded and linked
                if new_status == "succeeded" and intent.invoice_id:
                    stmt_inv = select(BillingInvoice).where(BillingInvoice.id == intent.invoice_id)
                    res_inv = await db.execute(stmt_inv)
                    invoice = res_inv.scalar_one_or_none()
                    if invoice:
                        invoice.status = "paid"
                        invoice.updated_at = utc_now()

                # Create Audit Event - NEVER LOG card or token or client_secret
                audit = PaymentAuditEvent(
                    id=uuid.uuid4(),
                    client_id=intent.client_id,
                    event_type=f"payment.{new_status}",
                    status="success",
                    provider="stripe",
                    actor_identifier="webhook",
                    metadata_json={
                        "provider_event_id": provider_event_id,
                        "provider_intent_id": provider_intent_id,
                        "old_status": old_status,
                        "new_status": new_status,
                    },
                )
                db.add(audit)
                webhook_event.status = "processed"
            else:
                webhook_event.status = "failed"
                webhook_event.error_message = f"PaymentIntent {provider_intent_id} not found."
        else:
            # Other unhandled event type
            webhook_event.status = "processed"

        await db.commit()
        return {"status": "success", "event_id": provider_event_id}
