from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from .contracts import BillingRepository, BillingPlanData

class SqlAlchemyBillingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _map_plan(self, plan: BillingPlan) -> BillingPlanData:
        return BillingPlanData(
            code=plan.code,
            name=plan.name,
            description=plan.description or "",
            rate_limit_per_minute=plan.rate_limit_per_minute,
            daily_token_quota=plan.daily_token_quota,
            weekly_token_quota=plan.weekly_token_quota,
            monthly_token_quota=plan.monthly_token_quota,
            max_output_tokens=plan.max_output_tokens,
            max_context_tokens=plan.max_context_tokens,
            allow_streaming=plan.allow_streaming,
            requests_per_day=plan.requests_per_day,
            requests_per_month=plan.requests_per_month,
            rag_enabled=plan.rag_enabled,
            rag_max_documents=plan.rag_max_documents,
            rag_max_storage_mb=plan.rag_max_storage_mb,
            rag_max_pages_per_month=plan.rag_max_pages_per_month,
            rag_max_queries_per_month=plan.rag_max_queries_per_month,
            tts_enabled=plan.tts_enabled,
            tts_chars_per_request=plan.tts_chars_per_request,
            tts_chars_per_day=plan.tts_chars_per_day,
            tts_chars_per_month=plan.tts_chars_per_month,
            tts_audio_retention_days=plan.tts_audio_retention_days,
            tts_max_files=plan.tts_max_files,
            embeddings_enabled=plan.embeddings_enabled,
            price_brl=Decimal(str(plan.price_brl)),
            is_active=plan.is_active
        )

    async def get_plan_by_code(self, code: str) -> Optional[BillingPlanData]:
        result = await self.db.execute(select(BillingPlan).where(BillingPlan.code == code))
        plan = result.scalar_one_or_none()
        if not plan:
            return None
        return self._map_plan(plan)

    async def list_plans(self) -> List[BillingPlanData]:
        result = await self.db.execute(select(BillingPlan))
        plans = result.scalars().all()
        return [self._map_plan(p) for p in plans]

    async def get_client_effective_plan(self, client_id: str) -> Optional[BillingPlanData]:
        from uuid import UUID
        try:
            client_uuid = UUID(client_id) if isinstance(client_id, str) else client_id
        except ValueError:
            return None
            
        result = await self.db.execute(
            select(BillingPlan).join(Client).where(Client.id == client_uuid)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            return None
        return self._map_plan(plan)

    async def record_usage(self, client_id: str, tokens: int, cost: Decimal) -> None:
        # This would typically interact with usage records or wallet
        # For now, it's a placeholder as requested in the initial implementation
        pass
