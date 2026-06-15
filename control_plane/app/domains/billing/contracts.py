from decimal import Decimal
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class BillingPlanData(BaseModel):
    code: str
    name: str
    description: str | None = None
    rate_limit_per_minute: int
    daily_token_quota: int
    weekly_token_quota: int
    monthly_token_quota: int
    max_output_tokens: int
    max_context_tokens: int = 4096
    allow_streaming: bool
    requests_per_day: int = 0
    requests_per_month: int = 0
    rag_enabled: bool = False
    rag_max_documents: int | None = None
    rag_max_storage_mb: int | None = None
    rag_max_pages_per_month: int | None = None
    rag_max_queries_per_month: int | None = None
    tts_enabled: bool = False
    tts_chars_per_request: int = 500
    tts_chars_per_day: int = 5000
    tts_chars_per_month: int = 50000
    tts_audio_retention_days: int = 7
    tts_max_files: int = 100
    embeddings_enabled: bool = False
    price_brl: Decimal = Decimal("0.00")
    is_active: bool = True


@runtime_checkable
class BillingRepository(Protocol):
    async def get_plan_by_code(self, code: str) -> BillingPlanData | None: ...
    async def list_plans(self) -> list[BillingPlanData]: ...
    async def get_client_effective_plan(self, client_id: str) -> BillingPlanData | None: ...
    async def record_usage(self, client_id: str, tokens: int, cost: Decimal) -> None: ...
