import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.services.billing.payments.mock_payment_provider import MockPaymentProvider
from app.services.billing.payments.stripe_provider import StripePaymentProvider
from app.services.billing.payments.mercadopago_provider import MercadoPagoPaymentProvider
from app.services.billing.payments.asaas_provider import AsaasPaymentProvider

settings = get_settings()

class PixService:
    @staticmethod
    def get_provider():
        p = settings.payment_provider
        if p == "stripe": return StripePaymentProvider()
        if p == "mercadopago": return MercadoPagoPaymentProvider()
        if p == "asaas": return AsaasPaymentProvider()
        return MockPaymentProvider()

    @classmethod
    async def create_payment(
        cls,
        db: AsyncSession,
        client_id: uuid.UUID,
        amount_cents: int,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        if not settings.pix_payment_enabled:
            raise ValueError("PIX payments are disabled")
        
        provider = cls.get_provider()
        return await provider.create_pix_payment(client_id, amount_cents, "brl", idempotency_key)
