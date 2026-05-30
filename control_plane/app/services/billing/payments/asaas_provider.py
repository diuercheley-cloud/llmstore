import uuid
import logging
from typing import Dict, Any, Optional
from app.services.billing.payments.payment_provider import PaymentProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AsaasPaymentProvider(PaymentProvider):
    def __init__(self):
        self.api_key = settings.asaas_api_key

    async def create_customer(self, client_id: uuid.UUID, name: str, email: Optional[str] = None) -> str:
        return f"cus_asaas_{uuid.uuid4().hex[:16]}"

    async def create_payment_intent(self, client_id: uuid.UUID, amount_cents: int, currency: str, provider_customer_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        return {"id": f"asaas_{uuid.uuid4().hex[:16]}", "status": "pending"}

    async def create_pix_payment(self, client_id: uuid.UUID, amount_cents: int, currency: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": f"pix_asaas_{uuid.uuid4().hex[:16]}",
            "qr_code": "ASAAS_PIX_QR_MOCK",
            "status": "pending"
        }

    async def create_card_payment(self, client_id: uuid.UUID, amount_cents: int, currency: str, payment_method_id: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        return {"id": f"pay_asaas_{uuid.uuid4().hex[:16]}", "status": "succeeded"}

    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        return True
