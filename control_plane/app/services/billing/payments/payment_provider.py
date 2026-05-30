# Owner: agent-platform
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PaymentProvider(ABC):
    @abstractmethod
    async def create_customer(
        self,
        client_id: uuid.UUID,
        name: str,
        email: Optional[str] = None
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
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
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
    async def retrieve_payment_intent(
        self,
        provider_intent_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves a payment intent from the provider.
        Expected return dict:
        {
            "id": "provider_intent_id",
            "amount_cents": int,
            "status": "requires_payment_method|succeeded|processing etc"
        }
        """
        pass
