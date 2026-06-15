# Owner: agent-platform
import uuid
from typing import Any

from app.services.billing.payments.payment_provider import PaymentProvider


class MockPaymentProvider(PaymentProvider):
    async def create_customer(
        self, client_id: uuid.UUID, name: str, email: str | None = None
    ) -> str:
        # Returns a mock customer ID
        return f"cus_mock_{uuid.uuid4().hex[:16]}"

    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        intent_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        client_secret = f"seti_mock_{uuid.uuid4().hex[:24]}"
        return {
            "id": intent_id,
            "client_secret": client_secret,
            "status": "succeeded",  # Default succeeded for immediate test validation
        }

    async def retrieve_payment_intent(self, provider_intent_id: str) -> dict[str, Any]:
        return {"id": provider_intent_id, "amount_cents": 1000, "status": "succeeded"}

    async def create_pix_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": f"pix_mock_{uuid.uuid4().hex[:16]}",
            "qr_code": "00020126360014br.gov.bcb.pix0114+5511999999999520400005303986540510.005802BR5908LLM STACK6009SAO PAULO62070503***6304ABCD",
            "qr_code_url": "https://example.com/pix/mock",
            "status": "pending",
        }

    async def create_card_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        payment_method_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return {"id": f"pay_mock_{uuid.uuid4().hex[:16]}", "status": "succeeded", "last4": "4242"}

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        return signature == "mock_valid_signature"
