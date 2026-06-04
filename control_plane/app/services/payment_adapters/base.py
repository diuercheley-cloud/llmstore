from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


class PaymentAdapterError(Exception):
    def __init__(self, message: str, *, code: str = "payment_adapter_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PaymentIntentResult:
    provider: str
    external_id: str
    idempotency_key: str
    status: str
    payment_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentWebhookPayload:
    provider: str
    external_id: str | None
    idempotency_key: str
    status: str
    amount_brl: Decimal
    paid_at: str | None = None


class BasePaymentAdapter(Protocol):
    provider: str

    async def create_topup_intent(
        self,
        *,
        client_id: uuid.UUID,
        amount_brl: Decimal,
        idempotency_key: str,
    ) -> PaymentIntentResult:
        ...

    def parse_webhook(self, payload: dict[str, Any]) -> PaymentWebhookPayload:
        ...
