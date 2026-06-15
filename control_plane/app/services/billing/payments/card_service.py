import uuid
from typing import Any

from app.core.config import get_settings
from app.services.billing.payments.asaas_provider import AsaasPaymentProvider
from app.services.billing.payments.mercadopago_provider import MercadoPagoPaymentProvider
from app.services.billing.payments.mock_payment_provider import MockPaymentProvider
from app.services.billing.payments.stripe_provider import StripePaymentProvider
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()


class CardService:
    @staticmethod
    def get_provider():
        p = settings.payment_provider
        if p == "stripe":
            return StripePaymentProvider()
        if p == "mercadopago":
            return MercadoPagoPaymentProvider()
        if p == "asaas":
            return AsaasPaymentProvider()
        return MockPaymentProvider()

    @classmethod
    async def create_payment(
        cls,
        db: AsyncSession,
        client_id: uuid.UUID,
        amount_cents: int,
        payment_method_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not settings.card_payment_enabled:
            raise ValueError("Card payments are disabled")

        provider = cls.get_provider()
        return await provider.create_card_payment(
            client_id, amount_cents, "brl", payment_method_id, idempotency_key
        )
