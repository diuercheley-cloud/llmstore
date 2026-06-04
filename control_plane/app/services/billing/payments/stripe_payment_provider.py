# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.services.billing.payments.payment_provider import PaymentProvider
from fastapi import HTTPException

logger = logging.getLogger("stripe_payment_provider")

class StripePaymentProvider(PaymentProvider):
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.stripe_secret_key

    def _verify_enabled(self):
        settings = get_settings()
        if not settings.stripe_payment_enabled:
            raise HTTPException(status_code=403, detail="Stripe payment is disabled.")
        if not settings.stripe_secret_key:
            raise HTTPException(status_code=400, detail="Stripe secret key is not configured.")

    async def create_customer(
        self,
        client_id: uuid.UUID,
        name: str,
        email: Optional[str] = None
    ) -> str:
        self._verify_enabled()
        import stripe
        stripe.api_key = self.api_key
        try:
            customer = stripe.Customer.create(
                name=name,
                email=email,
                metadata={"client_id": str(client_id)}
            )
            return customer.id
        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        self._verify_enabled()
        import stripe
        stripe.api_key = self.api_key
        try:
            # Create payment intent with metadata and idempotency key
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                customer=provider_customer_id,
                metadata={"client_id": str(client_id)},
                idempotency_key=idempotency_key
            )
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status
            }
        except Exception as e:
            logger.error(f"Failed to create Stripe payment intent: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    async def retrieve_payment_intent(
        self,
        provider_intent_id: str
    ) -> Dict[str, Any]:
        self._verify_enabled()
        import stripe
        stripe.api_key = self.api_key
        try:
            intent = stripe.PaymentIntent.retrieve(provider_intent_id)
            return {
                "id": intent.id,
                "amount_cents": intent.amount,
                "status": intent.status
            }
        except Exception as e:
            logger.error(f"Failed to retrieve Stripe payment intent: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
