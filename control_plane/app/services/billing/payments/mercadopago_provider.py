import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.services.billing.payments.payment_provider import PaymentProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class MercadoPagoPaymentProvider(PaymentProvider):
    def __init__(self):
        self.access_token = settings.mercadopago_access_token

    async def create_customer(
        self, client_id: uuid.UUID, name: str, email: str | None = None
    ) -> str:
        return f"cus_mp_{uuid.uuid4().hex[:16]}"

    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return {"id": f"mp_{uuid.uuid4().hex[:16]}", "status": "pending"}

    async def create_pix_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": f"pix_mp_{uuid.uuid4().hex[:16]}",
            "qr_code": "MERCADOPAGO_PIX_QR_MOCK",
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
        return {"id": f"pay_mp_{uuid.uuid4().hex[:16]}", "status": "succeeded"}

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        return True
