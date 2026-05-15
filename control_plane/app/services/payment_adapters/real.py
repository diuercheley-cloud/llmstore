from __future__ import annotations

from decimal import Decimal
from typing import Any
import uuid

from app.core.config import get_settings
from app.services.payment_adapters.base import PaymentAdapterError, PaymentIntentResult, PaymentWebhookPayload


class RealPaymentAdapter:
    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def create_topup_intent(
        self,
        *,
        client_id: uuid.UUID,
        amount_brl: Decimal,
        idempotency_key: str,
    ) -> PaymentIntentResult:
        settings = get_settings()
        if not settings.payment_real_enabled:
            raise PaymentAdapterError(
                "real payment provider is disabled; set PAYMENT_REAL_ENABLED=true to opt in",
                code="payment_real_disabled",
            )
        raise PaymentAdapterError(
            f"real payment provider '{self.provider}' is not implemented in this build",
            code="payment_provider_not_implemented",
        )

    def parse_webhook(self, payload: dict[str, Any]) -> PaymentWebhookPayload:
        settings = get_settings()
        if not settings.payment_real_enabled:
            raise PaymentAdapterError(
                "real payment provider is disabled; set PAYMENT_REAL_ENABLED=true to opt in",
                code="payment_real_disabled",
            )
        external_id = payload.get("external_id") or payload.get("id")
        idempotency_key = payload.get("idempotency_key") or external_id
        if not idempotency_key:
            raise PaymentAdapterError("webhook missing idempotency_key", code="webhook_missing_idempotency")
        try:
            amount_brl = Decimal(str(payload.get("amount_brl")))
        except Exception as exc:
            raise PaymentAdapterError("webhook has invalid amount_brl", code="webhook_invalid_amount") from exc
        return PaymentWebhookPayload(
            provider=self.provider,
            external_id=str(external_id) if external_id else None,
            idempotency_key=str(idempotency_key),
            status=str(payload.get("status") or "pending"),
            amount_brl=amount_brl,
            paid_at=payload.get("paid_at"),
        )
