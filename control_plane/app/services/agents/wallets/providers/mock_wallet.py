# Owner: agent-platform
import uuid
from typing import Any


class MockWalletProvider:
    async def process_payment(self, amount: float, currency: str) -> dict[str, Any]:
        return {
            "status": "success",
            "provider": "mock",
            "transaction_id": str(uuid.uuid4()),
            "receipt_url": "http://internal-receipt.local/123",
        }
