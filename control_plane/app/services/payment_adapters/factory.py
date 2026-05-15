from app.core.config import get_settings
from app.services.payment_adapters.base import PaymentAdapterError
from app.services.payment_adapters.mock import MockPaymentAdapter
from app.services.payment_adapters.real import RealPaymentAdapter


def get_payment_adapter(provider: str | None = None):
    settings = get_settings()
    selected = (provider or settings.payment_provider or "disabled").strip().lower()
    if selected == "disabled":
        raise PaymentAdapterError("payment provider is disabled", code="payment_provider_disabled")
    if selected == "mock":
        return MockPaymentAdapter()
    if not settings.payment_real_enabled:
        raise PaymentAdapterError(
            "real payment providers are disabled by default",
            code="payment_real_disabled",
        )
    return RealPaymentAdapter(selected)
