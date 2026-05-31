import uuid
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional

from app.services.billing.payments.payment_provider import PaymentProvider

logger = logging.getLogger(__name__)

try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False


class StripePaymentProvider(PaymentProvider):
    """
    Stripe implementation of the PaymentProvider interface.
    Gracefully degrades when stripe library or API key is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self._available = HAS_STRIPE and bool(api_key)

        if HAS_STRIPE and api_key:
            stripe.api_key = api_key
            logger.info("Stripe payment provider initialized")
        else:
            logger.warning(
                "Stripe payment provider initialized in degraded mode"
                f" (stripe library: {HAS_STRIPE}, api_key configured: {bool(api_key)})"
            )

    async def create_customer(
        self,
        client_id: uuid.UUID,
        name: str,
        email: Optional[str] = None,
    ) -> str:
        if not self._available:
            return f"mock_customer_{client_id}"

        customer = stripe.Customer.create(
            name=name,
            email=email,
            metadata={"client_id": str(client_id)},
        )
        logger.info(f"Created Stripe customer {customer.id} for {client_id}")
        return customer.id

    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._available:
            return {
                "id": f"mock_pi_{uuid.uuid4()}",
                "client_secret": f"mock_secret_{uuid.uuid4()}",
                "status": "requires_payment_method",
            }

        kwargs = {
            "amount": amount_cents,
            "currency": currency.lower(),
            "customer": provider_customer_id,
            "metadata": {"client_id": str(client_id)},
        }
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        intent = stripe.PaymentIntent.create(**kwargs)
        return {
            "id": intent.id,
            "client_secret": intent.client_secret,
            "status": intent.status,
        }

    async def create_pix_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._available or currency.upper() != "BRL":
            return {
                "id": f"mock_pix_{uuid.uuid4()}",
                "qr_code": "000201010212261060014br.gov.bcb.pix2588mock-qr-code-string",
                "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAkCAYAAABIdFEMAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAHhJREFUeNpi",
                "status": "pending",
                "expires_at": None,
            }

        kwargs = {
            "amount": amount_cents,
            "currency": "brl",
            "payment_method_types": ["pix"],
            "metadata": {"client_id": str(client_id)},
        }
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        intent = stripe.PaymentIntent.create(**kwargs)
        return {
            "id": intent.id,
            "qr_code": intent.next_action.pix_display_qr_code if intent.next_action else "mock-qr-code",
            "qr_code_base64": intent.next_action.pix_display_qr_code_data if intent.next_action else "mock-base64",
            "status": intent.status,
            "expires_at": intent.next_action.pix_display_qr_code_expires_at if intent.next_action else None,
        }

    async def create_card_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        payment_method_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._available:
            return {
                "id": f"mock_card_{uuid.uuid4()}",
                "status": "succeeded",
            }

        kwargs = {
            "amount": amount_cents,
            "currency": currency.lower(),
            "payment_method": payment_method_id,
            "confirm": True,
            "metadata": {"client_id": str(client_id)},
        }
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        intent = stripe.PaymentIntent.create(**kwargs)
        return {
            "id": intent.id,
            "status": intent.status,
        }

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        if not self._available or not self.webhook_secret:
            return bool(signature)
        try:
            stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
            return True
        except Exception as e:
            logger.warning(f"Stripe webhook validation failed: {e}")
            return False
