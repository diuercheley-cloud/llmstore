# Owner: platform-ops
from app.db.session import get_db_session
from app.models.request_financial import RequestFinancial
from app.services.auth import require_admin
from app.services.billing.pricing_engine import (
    calculate_financials,
    get_provider_pricing_config,
)
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/billing",
    tags=["admin", "billing"],
    dependencies=[Depends(require_admin)],
)


class PricingSimulateRequest(BaseModel):
    provider: str = Field(default="local")
    prompt_tokens: int = Field(default=100, ge=0)
    completion_tokens: int = Field(default=50, ge=0)
    cache_hit: bool = False
    plan_code: str | None = "basic"


class ProviderCostRead(BaseModel):
    provider: str
    cost_usd_per_1k_prompt: float
    cost_usd_per_1k_completion: float
    pricing_configured: bool


class MarginSummaryRead(BaseModel):
    provider: str
    total_requests: int
    total_provider_cost_brl: float
    total_customer_price_brl: float
    total_gross_profit_brl: float
    avg_margin_percent: float | None


class UsageFinancialRead(BaseModel):
    id: str
    client_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cache_hit: bool
    provider_cost_usd: float | None
    provider_cost_brl: float | None
    customer_price_brl: float | None
    gross_profit_brl: float | None
    margin_percent: float | None
    created_at: str


@router.get("/provider-costs", response_model=list[ProviderCostRead])
async def get_provider_costs():
    pricing = get_provider_pricing_config()
    providers = pricing.get("providers", {})
    result = []
    for pid, cfg in providers.items():
        result.append(ProviderCostRead(
            provider=pid,
            cost_usd_per_1k_prompt=float(cfg.get("cost_usd_per_1k_prompt", 0.0)),
            cost_usd_per_1k_completion=float(cfg.get("cost_usd_per_1k_completion", 0.0)),
            pricing_configured=cfg.get("pricing_configured", False),
        ))
    return result


@router.get("/margins/summary", response_model=list[MarginSummaryRead])
async def get_margins_summary(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=500),
):
    stmt = (
        select(
            RequestFinancial.provider,
            func.count(RequestFinancial.id).label("total_requests"),
            func.sum(RequestFinancial.provider_cost_brl).label("total_provider_cost_brl"),
            func.sum(RequestFinancial.customer_price_brl).label("total_customer_price_brl"),
            func.sum(RequestFinancial.gross_profit_brl).label("total_gross_profit_brl"),
            func.avg(RequestFinancial.margin_percent).label("avg_margin_percent"),
        )
        .group_by(RequestFinancial.provider)
        .order_by(desc("total_requests"))
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()
    output = []
    for row in rows:
        output.append(MarginSummaryRead(
            provider=row.provider,
            total_requests=int(row.total_requests),
            total_provider_cost_brl=float(row.total_provider_cost_brl or 0.0),
            total_customer_price_brl=float(row.total_customer_price_brl or 0.0),
            total_gross_profit_brl=float(row.total_gross_profit_brl or 0.0),
            avg_margin_percent=float(row.avg_margin_percent) if row.avg_margin_percent is not None else None,
        ))
    return output


@router.get("/usage-financials", response_model=list[UsageFinancialRead])
async def get_usage_financials(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=500),
    client_id: str | None = None,
):
    stmt = (
        select(RequestFinancial)
        .order_by(desc(RequestFinancial.created_at))
        .limit(limit)
    )
    if client_id:
        stmt = (
            select(RequestFinancial)
            .where(RequestFinancial.client_id == client_id)
            .order_by(desc(RequestFinancial.created_at))
            .limit(limit)
        )
    result = await session.execute(stmt)
    records = result.scalars().all()
    output = []
    for r in records:
        output.append(UsageFinancialRead(
            id=str(r.id),
            client_id=str(r.client_id),
            provider=r.provider,
            model=r.model,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            total_tokens=r.total_tokens,
            cache_hit=r.cache_hit,
            provider_cost_usd=float(r.provider_cost_usd) if r.provider_cost_usd is not None else None,
            provider_cost_brl=float(r.provider_cost_brl) if r.provider_cost_brl is not None else None,
            customer_price_brl=float(r.customer_price_brl) if r.customer_price_brl is not None else None,
            gross_profit_brl=float(r.gross_profit_brl) if r.gross_profit_brl is not None else None,
            margin_percent=float(r.margin_percent) if r.margin_percent is not None else None,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))
    return output


@router.post("/pricing/simulate")
async def simulate_pricing(req: PricingSimulateRequest):
    result = calculate_financials(
        provider=req.provider,
        prompt_tokens=req.prompt_tokens,
        completion_tokens=req.completion_tokens,
        cache_hit=req.cache_hit,
        plan_code=req.plan_code,
    )
    return result
