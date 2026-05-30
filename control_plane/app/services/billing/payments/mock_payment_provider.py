# Owner: agent-platform
import uuid
from typing import Dict, Any, Optional
from app.services.billing.payments.payment_provider import PaymentProvider

class MockPaymentProvider(PaymentProvider):
    async def create_customer(
        self,
        client_id: uuid.UUID,
        name: str,
        email: Optional[str] = None
    ) -> str:
        # Returns a mock customer ID
        return f"cus_mock_{uuid.uuid4().hex[:16]}"

    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        intent_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        client_secret = f"seti_mock_{uuid.uuid4().hex[:24]}"
        return {
            "id": intent_id,
            "client_secret": client_secret,
            "status": "succeeded" # Default succeeded for immediate test validation
        }

    async def retrieve_payment_intent(
        self,
        provider_intent_id: str
    ) -> Dict[str, Any]:
        return {
            "id": provider_intent_id,
            "amount_cents": 1000,
            "status": "succeeded"
        }
