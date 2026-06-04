# Owner: platform-ops
import logging
from datetime import date, datetime, timezone

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.client import Client
from app.models.request_financial import RequestFinancial
from app.services.auth import require_admin
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/admin/saas",
    tags=["admin", "saas"],
    dependencies=[Depends(require_admin)],
)

@router.get("/overview")
async def saas_overview(
    session: AsyncSession = Depends(get_db_session),
):
    today = date.today()
    
    # 1. Client counts
    total_clients = 0
    active_clients = 0
    try:
        total_stmt = select(func.count(Client.id))
        total_clients = (await session.execute(total_stmt)).scalar() or 0
        
        active_stmt = select(func.count(Client.id)).where(Client.is_active == True)
        active_clients = (await session.execute(active_stmt)).scalar() or 0
    except Exception as e:
        logger.error(f"Error fetching client counts: {e}")

    # 2. Financials today
    requests_today = 0
    provider_cost_today = 0.0
    revenue_today = 0.0
    margin_today = 0.0
    
    try:
        financial_stmt = select(
            func.count(RequestFinancial.id).label("requests"),
            func.sum(RequestFinancial.provider_cost_brl).label("cost"),
            func.sum(RequestFinancial.customer_price_brl).label("revenue"),
            func.sum(RequestFinancial.gross_profit_brl).label("profit")
        ).where(func.date(RequestFinancial.created_at) == today)
        
        row = (await session.execute(financial_stmt)).first()
        if row:
            requests_today = row.requests or 0
            provider_cost_today = float(row.cost or 0.0)
            revenue_today = float(row.revenue or 0.0)
            profit_today = float(row.profit or 0.0)
            if revenue_today > 0:
                margin_today = (profit_today / revenue_today) * 100
    except Exception as e:
        logger.error(f"Error fetching today financials: {e}")

    # 3. Guardrails
    blocked_by_cost = False
    if settings.deployment_mode == "saas":
        if settings.max_global_provider_cost_per_day_brl > 0 and provider_cost_today >= settings.max_global_provider_cost_per_day_brl:
            blocked_by_cost = True

    return {
        "deployment_mode": settings.deployment_mode,
        "total_clients": total_clients,
        "active_clients": active_clients,
        "requests_today": requests_today,
        "provider_cost_today_brl": round(provider_cost_today, 2),
        "revenue_today_brl": round(revenue_today, 2),
        "margin_today_percent": round(margin_today, 2),
        "blocked_by_cost_guardrail": blocked_by_cost,
        "global_cost_limit_brl": settings.max_global_provider_cost_per_day_brl,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
