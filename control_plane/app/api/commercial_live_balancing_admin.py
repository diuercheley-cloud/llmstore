# Owner: commercial-ops
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.services.routing.commercial_live_balancer import CommercialLiveBalancer
from app.models.commercial_cluster_registry import CommercialClusterRegistry

router = APIRouter()

@router.get("/overview")
async def get_overview(_: dict = Depends(require_admin)):
    settings = get_settings()
    
    return {
        "status": "success",
        "enabled": settings.commercial_live_balancing_enabled,
        "mode": settings.commercial_live_balancing_mode,
        "min_margin_percent": settings.commercial_live_balancing_min_margin_percent,
        "max_latency_ms": settings.commercial_live_balancing_max_latency_ms
    }

@router.get("/opportunities")
async def get_opportunities(db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    balancer = CommercialLiveBalancer()
    
    # Mocking cluster metrics for this endpoint
    res = await db.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.status == "active"))
    clusters = list(res.scalars().all())
    
    metrics = []
    for c in clusters:
        metrics.append({
            "cluster_id": c.cluster_id,
            "margin_percent": 15.0 if "low" in c.cluster_id else 40.0,
            "avg_latency_ms": 6000 if "slow" in c.cluster_id else 150
        })
        
    opportunities = balancer.summarize_balancing_opportunities(metrics)
    
    return {
        "status": "success",
        "opportunities": opportunities
    }

@router.post("/simulate")
async def simulate_live_balancing(payload: dict, _: dict = Depends(require_admin)):
    balancer = CommercialLiveBalancer()
    
    current_state = payload.get("current_state", {"traffic_percent": 50})
    metrics = payload.get("metrics", {"margin_percent": 10.0})
    history = payload.get("history", [])
    
    recommendation = balancer.recommend_rebalance("target-cluster", metrics, history)
    
    if recommendation["action"] != "none":
        is_flapping = balancer.detect_flapping("target-cluster", recommendation.get("target_decrease_percent", 0), history)
        if is_flapping:
            recommendation["action"] = "none"
            recommendation["reason"] = "blocked_by_anti_flapping"
            
    simulation = balancer.simulate_rebalance(current_state, recommendation)
    
    return {
        "status": "success",
        "recommendation": recommendation,
        "simulation": simulation
    }