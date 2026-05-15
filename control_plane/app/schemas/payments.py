from decimal import Decimal

from pydantic import BaseModel, Field


class WalletTopUpCreate(BaseModel):
    amount_brl: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)
