from __future__ import annotations

from decimal import Decimal
from typing import Any
import uuid

from app.services.payment_adapters.base import PaymentAdapterError, PaymentIntentResult, PaymentWebhookPayload


class MockPaymentAdapter:
    provider = "mock"

    async def create_topup_intent(
        self,
        *,
        client_id: uuid.UUID,
        amount_brl: Decimal,
        idempotency_key: str,
    ) -> PaymentIntentResult:
        external_id = f"mock_topup_{uuid.uuid4().hex[:24]}"
        amount_text = f"{amount_brl:.2f}"
        return PaymentIntentResult(
            provider=self.provider,
            external_id=external_id,
            idempotency_key=idempotency_key,
            status="pending",
            payment_data={
                "mode": "mock",
                "pix_copy_paste": f"MOCK-PIX-{external_id}-{amount_text}",
                "qr_code_text": f"mock pix {external_id} BRL {amount_text}",
                "expires_in_seconds": 1800,
            },
        )

    def parse_webhook(self, payload: dict[str, Any]) -> PaymentWebhookPayload:
        external_id = payload.get("external_id") or payload.get("payment_id")
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
