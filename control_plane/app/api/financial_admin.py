# Owner: platform-ops
from datetime import datetime, timezone, time as dt_time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import cast
from sqlalchemy.types import Integer

from app.db.session import get_db_session
from app.models.request_financial import RequestFinancial
from app.services.auth import require_admin
from app.services.billing.financial_reconciliation import FinancialReconciliationService
from app.services.billing.dispute_management import DisputeManagementService
from app.services.billing.financial_audit_trail import FinancialAuditTrailService

router = APIRouter(
    prefix="/admin/financials",
    tags=["admin", "financials"],
    dependencies=[Depends(require_admin)],
)

class ProviderStats(BaseModel):
    provider: str
    requests: int
    cost_brl: float

class ClientStats(BaseModel):
    client_id: str
    requests: int
    revenue_brl: float

class MarginClientAlert(BaseModel):
    client_id: str
    margin_percent: float
    gross_profit_brl: float

class ModelCostStats(BaseModel):
    model: str
    requests: int
    total_cost_brl: float

class ClientProfitStats(BaseModel):
    client_id: str
    profit_brl: float
    margin_percent: float

class FinancialSummary(BaseModel):
    mismatches_count: int
    open_disputes_count: int
    total_disputed_amount_brl: float
    audit_chain_valid: bool

class MarginDashboardResponse(BaseModel):
    generated_at_utc: datetime
    revenue_today_brl: float
    cost_today_brl: float
    gross_margin_today_brl: float
    gross_margin_percent_today: float
    requests_today: int
    cache_hit_rate_today: float
    estimated_cache_savings_brl: float
    requests_by_provider: list[ProviderStats]
    requests_by_client: list[ClientStats]
    cost_by_provider: list[ProviderStats]
    revenue_by_client: list[ClientStats]
    clients_with_negative_margin: list[MarginClientAlert]
    top_expensive_models: list[ModelCostStats]
    top_profitable_clients: list[ClientProfitStats]
    top_loss_clients: list[ClientProfitStats]
    financial_summary: FinancialSummary

@router.get("/margin-dashboard", response_model=MarginDashboardResponse)
async def get_margin_dashboard(session: AsyncSession = Depends(get_db_session)):
    now_utc = datetime.now(timezone.utc)
    today_start = datetime.combine(now_utc.date(), dt_time.min, tzinfo=timezone.utc)

    stmt_globals = select(
        func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("rev"),
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost"),
        func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit"),
        func.count(RequestFinancial.id).label("reqs"),
        func.coalesce(func.sum(cast(RequestFinancial.cache_hit, Integer)), 0).label("hits")
    ).where(RequestFinancial.created_at >= today_start)
    
    res_globals = (await session.execute(stmt_globals)).first()
    rev = float(res_globals.rev or 0.0)
    cost = float(res_globals.cost or 0.0)
    profit = float(res_globals.profit or 0.0)
    reqs = int(res_globals.reqs or 0)
    hits = int(res_globals.hits or 0)
    
    margin_pct = (profit / rev * 100.0) if rev > 0 else 0.0
    hit_rate = (hits / reqs * 100.0) if reqs > 0 else 0.0
    
    cache_savings = 0.0
    cache_misses = max(reqs - hits, 0)
    if hits > 0 and cache_misses > 0:
        avg_miss_cost = cost / cache_misses
        cache_savings = avg_miss_cost * hits

    stmt_provider = select(
        RequestFinancial.provider,
        func.count(RequestFinancial.id).label("reqs"),
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost")
    ).where(RequestFinancial.created_at >= today_start).group_by(RequestFinancial.provider)
    res_prov = (await session.execute(stmt_provider)).all()
    
    reqs_by_prov = []
    cost_by_prov = []
    for r in res_prov:
        reqs_by_prov.append(ProviderStats(provider=r.provider or "unknown", requests=int(r.reqs), cost_brl=float(r.cost or 0.0)))
        cost_by_prov.append(ProviderStats(provider=r.provider or "unknown", requests=int(r.reqs), cost_brl=float(r.cost or 0.0)))
        
    reqs_by_prov.sort(key=lambda x: x.requests, reverse=True)
    cost_by_prov.sort(key=lambda x: x.cost_brl, reverse=True)

    stmt_client = select(
        RequestFinancial.client_id,
        func.count(RequestFinancial.id).label("reqs"),
        func.coalesce(func.sum(RequestFinancial.customer_price_brl), 0).label("rev"),
        func.coalesce(func.sum(RequestFinancial.gross_profit_brl), 0).label("profit")
    ).where(RequestFinancial.created_at >= today_start).group_by(RequestFinancial.client_id)
    res_cli = (await session.execute(stmt_client)).all()
    
    reqs_by_cli = []
    rev_by_cli = []
    prof_by_cli = []
    clients_negative = []
    
    for r in res_cli:
        client_id = str(r.client_id)
        c_reqs = int(r.reqs)
        c_rev = float(r.rev or 0.0)
        c_prof = float(r.profit or 0.0)
        c_margin = (c_prof / c_rev * 100.0) if c_rev > 0 else 0.0

        reqs_by_cli.append(ClientStats(client_id=client_id, requests=c_reqs, revenue_brl=c_rev))
        rev_by_cli.append(ClientStats(client_id=client_id, requests=c_reqs, revenue_brl=c_rev))
        prof_by_cli.append(ClientProfitStats(client_id=client_id, profit_brl=c_prof, margin_percent=c_margin))

        if c_prof < 0:
            clients_negative.append(MarginClientAlert(client_id=client_id, margin_percent=c_margin, gross_profit_brl=c_prof))

    reqs_by_cli.sort(key=lambda x: x.requests, reverse=True)
    rev_by_cli.sort(key=lambda x: x.revenue_brl, reverse=True)
    
    top_profitable = sorted(prof_by_cli, key=lambda x: x.profit_brl, reverse=True)[:10]
    top_loss = sorted([p for p in prof_by_cli if p.profit_brl < 0], key=lambda x: x.profit_brl)[:10]

    stmt_model = select(
        RequestFinancial.model,
        func.count(RequestFinancial.id).label("reqs"),
        func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0).label("cost")
    ).where(RequestFinancial.created_at >= today_start).group_by(RequestFinancial.model).order_by(desc(func.coalesce(func.sum(RequestFinancial.provider_cost_brl), 0))).limit(10)
    res_mod = (await session.execute(stmt_model)).all()
    
    top_models = []
    for r in res_mod:
        top_models.append(ModelCostStats(model=r.model or "unknown", requests=int(r.reqs), total_cost_brl=float(r.cost or 0.0)))

    # Phase 27 Financial Summary
    recon_summary = await FinancialReconciliationService.summarize_reconciliation(session)
    dispute_summary = await DisputeManagementService.summarize_disputes(session)
    audit_chain_valid = await FinancialAuditTrailService.validate_audit_chain(session)
    
    mismatches_count = recon_summary.get("mismatch", {}).get("count", 0)
    open_disputes_count = dispute_summary.get("open", {}).get("count", 0)
    total_disputed_amount = sum(s.get("total_claimed", 0) for s in dispute_summary.values())

    return MarginDashboardResponse(
        generated_at_utc=now_utc,
        revenue_today_brl=rev,
        cost_today_brl=cost,
        gross_margin_today_brl=profit,
        gross_margin_percent_today=margin_pct,
        requests_today=reqs,
        cache_hit_rate_today=hit_rate,
        estimated_cache_savings_brl=cache_savings,
        requests_by_provider=reqs_by_prov,
        requests_by_client=reqs_by_cli,
        cost_by_provider=cost_by_prov,
        revenue_by_client=rev_by_cli,
        clients_with_negative_margin=clients_negative,
        top_expensive_models=top_models,
        top_profitable_clients=top_profitable,
        top_loss_clients=top_loss,
        financial_summary=FinancialSummary(
            mismatches_count=mismatches_count,
            open_disputes_count=open_disputes_count,
            total_disputed_amount_brl=total_disputed_amount,
            audit_chain_valid=audit_chain_valid
        )
    )
