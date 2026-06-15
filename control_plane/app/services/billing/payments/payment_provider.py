# Owner: agent-platform
import uuid
from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    @abstractmethod
    async def create_customer(
        self, client_id: uuid.UUID, name: str, email: str | None = None
    ) -> str:
        """
        Creates a customer in the billing system and returns the provider customer ID.
        """
        pass

    @abstractmethod
    async def create_payment_intent(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        provider_customer_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Creates a payment intent on the provider and returns intent details.
        Expected return dict:
        {
            "id": "provider_intent_id",
            "client_secret": "secret_hash",
            "status": "requires_payment_method|succeeded|processing etc"
        }
        """
        pass

    @abstractmethod
    async def create_pix_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Creates a PIX payment and returns payment details including QR code.
        """
        pass

    @abstractmethod
    async def create_card_payment(
        self,
        client_id: uuid.UUID,
        amount_cents: int,
        currency: str,
        payment_method_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Creates a card payment using a tokenized payment method.
        """
        pass

    @abstractmethod
    async def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Validates the webhook signature from the provider.
        """
        pass
