from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def calculate_estimation_error(
    db: AsyncSession,
    days: int = 7,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    min_samples: int = 20
) -> Dict[str, Any]:
    """
    Calculates the error between estimated and actual financials with outlier protection.
    """
    settings = get_settings()
    lookback = datetime.now(timezone.utc) - timedelta(days=days)
    
    filters = [
        CommercialRoutingEvent.created_at >= lookback,
        CommercialRoutingEvent.actual_cost_brl.is_not(None),
        CommercialRoutingEvent.actual_cost_brl > 0
    ]
    
    if provider:
        filters.append(CommercialRoutingEvent.selected_provider == provider)
    if model:
        filters.append(CommercialRoutingEvent.selected_model == model)
        
    # Get all costs to calculate median, p95 and trimmed mean
    stmt = select(
        CommercialRoutingEvent.estimated_cost_brl,
        CommercialRoutingEvent.actual_cost_brl
    ).where(*filters).order_by(desc(CommercialRoutingEvent.created_at))
    
    res = await db.execute(stmt)
    rows = res.all()
    sample_count = len(rows)
    
    if sample_count < min_samples:
        return {
            "sample_count": sample_count,
            "confidence": "low",
            "reason": f"Insufficient data (need {min_samples}, got {sample_count})"
        }
        
    est_costs = [float(r[0]) for r in rows]
    act_costs = [float(r[1]) for r in rows]
    
    # Simple average
    avg_est = sum(est_costs) / sample_count
    avg_act = sum(act_costs) / sample_count
    
    # Sorted for percentiles
    sorted_act = sorted(act_costs)
    median_act = sorted_act[sample_count // 2]
    p95_act = sorted_act[int(sample_count * 0.95)]
    
    # Trimmed mean
    if settings.commercial_calibration_use_trimmed_mean and sample_count >= 10:
        trim_pct = settings.commercial_calibration_outlier_trim_percent / 100.0
        trim_count = int(sample_count * trim_pct)
        if trim_count > 0:
            # We also need to trim est_costs correspondingly if we want "paired" trimmed mean
            # To keep it consistent, let's pair them.
            indexed_costs = sorted(zip(act_costs, est_costs), key=lambda x: x[0])
            trimmed_paired = indexed_costs[trim_count:-trim_count]
            
            avg_act_final = sum(p[0] for p in trimmed_paired) / len(trimmed_paired)
            avg_est_final = sum(p[1] for p in trimmed_paired) / len(trimmed_paired)
        else:
            avg_act_final = avg_act
            avg_est_final = avg_est
    else:
        avg_act_final = avg_act
        avg_est_final = avg_est

    cost_error_brl = avg_est_final - avg_act_final
    cost_error_pct = (cost_error_brl / avg_act_final) * 100 if avg_act_final > 0 else 0
    
    confidence = "high" if sample_count >= min_samples * 5 else "medium"
    
    return {
        "sample_count": sample_count,
        "avg_estimated_cost": round(avg_est_final, 6),
        "avg_actual_cost": round(avg_act_final, 6),
        "median_actual_cost": round(median_act, 6),
        "p95_actual_cost": round(p95_act, 6),
        "cost_error_brl": round(cost_error_brl, 6),
        "cost_error_percent": round(cost_error_pct, 2),
        "confidence": confidence,
        "trimmed": settings.commercial_calibration_use_trimmed_mean and sample_count >= 10
    }

async def summarize_error_by_provider(db: AsyncSession, days: int = 7) -> List[Dict[str, Any]]:
    """
    Groups error summary by provider.
    """
    lookback = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = select(
        CommercialRoutingEvent.selected_provider,
        func.count(CommercialRoutingEvent.id).label("count")
    ).where(
        and_(
            CommercialRoutingEvent.created_at >= lookback,
            CommercialRoutingEvent.actual_cost_brl.is_not(None)
        )
    ).group_by(CommercialRoutingEvent.selected_provider)
    
    result = await db.execute(stmt)
    providers = [row[0] for row in result.all() if row[0]]
    
    summaries = []
    for p in providers:
        summary = await calculate_estimation_error(db, days=days, provider=p, min_samples=1)
        summary["provider"] = p
        summaries.append(summary)
        
    return summaries

async def summarize_error_by_model(db: AsyncSession, days: int = 7) -> List[Dict[str, Any]]:
    """
    Groups error summary by model.
    """
    lookback = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = select(
        CommercialRoutingEvent.selected_provider,
        CommercialRoutingEvent.selected_model,
        func.count(CommercialRoutingEvent.id).label("count")
    ).where(
        and_(
            CommercialRoutingEvent.created_at >= lookback,
            CommercialRoutingEvent.actual_cost_brl.is_not(None)
        )
    ).group_by(CommercialRoutingEvent.selected_provider, CommercialRoutingEvent.selected_model)
    
    result = await db.execute(stmt)
    models = result.all()
    
    summaries = []
    for p, m, count in models:
        if not p or not m: continue
        summary = await calculate_estimation_error(db, days=days, provider=p, model=m, min_samples=1)
        summary["provider"] = p
        summary["model"] = m
        summaries.append(summary)
        
    return summaries

def recommend_cost_multiplier(
    avg_error_pct: float, 
    confidence: str,
    max_multiplier: float = 3.0,
    min_multiplier: float = 0.5
) -> float:
    """
    Recommends a cost multiplier based on the error percentage.
    """
    if confidence == "low":
        return 1.0
        
    settings = get_settings()
    max_change = settings.commercial_calibration_max_recommended_change_percent / 100.0
    
    # actual = estimated / (1 + error/100)
    # multiplier = actual / estimated = 1 / (1 + error/100)
    
    multiplier = 1.0 / (1 + (avg_error_pct / 100.0))
    
    # Apply max change limit (e.g. if max_change is 25%, multiplier must be between 0.75 and 1.25)
    lower_limit = 1.0 - max_change
    upper_limit = 1.0 + max_change
    
    multiplier = max(lower_limit, min(upper_limit, multiplier))
    
    # Final safety cap from parameters
    return max(min_multiplier, min(max_multiplier, multiplier))

async def recommend_weight_adjustments(
    db: AsyncSession, 
    days: int = 7,
    settings: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Recommends adjustments to routing weights.
    """
    # This is a placeholder for more complex logic.
    # Logic based on the prompt:
    # - aumentar peso de margem quando erro de custo estiver alto
    # - aumentar peso de latência quando provider tiver latência real maior que estimada
    # - reduzir bônus de provider com margem real baixa
    # - manter local_bonus quando local tiver margem alta e latência aceitável
    
    recommendations = []
    
    # Global margin weight recommendation
    error_summary = await calculate_estimation_error(db, days=days, min_samples=10)
    if error_summary.get("confidence") != "low":
        err_pct = error_summary.get("cost_error_percent", 0)
        if err_pct < -15: # Estimated is much lower than actual
            recommendations.append({
                "target": "commercial_margin_weight",
                "current": 0.60, # Default
                "recommended": 0.70,
                "reason": f"High cost estimation error ({err_pct}%). Increasing margin weight to prioritize safer routes."
            })

    return recommendations

async def generate_calibration_report(
    db: AsyncSession, 
    days: int = 7, 
    min_samples: int = 20,
    max_multiplier: float = 3.0,
    min_multiplier: float = 0.5
) -> Dict[str, Any]:
    """
    Generates a full calibration report.
    """
    global_error = await calculate_estimation_error(db, days=days, min_samples=min_samples)
    by_provider = await summarize_error_by_provider(db, days=days)
    by_model = await summarize_error_by_model(db, days=days)
    
    multipliers = []
    for m_summary in by_model:
        if m_summary.get("confidence") != "low":
            mult = recommend_cost_multiplier(
                m_summary["cost_error_percent"], 
                m_summary["confidence"],
                max_multiplier=max_multiplier,
                min_multiplier=min_multiplier
            )
            if abs(mult - 1.0) > 0.05: # Only recommend if change > 5%
                multipliers.append({
                    "provider": m_summary["provider"],
                    "model": m_summary["model"],
                    "sample_count": m_summary["sample_count"],
                    "avg_cost_error_percent": m_summary["cost_error_percent"],
                    "recommended_cost_multiplier": round(mult, 2),
                    "confidence": m_summary["confidence"],
                    "reason": "actual cost is higher than estimated cost" if mult > 1.0 else "actual cost is lower than estimated cost"
                })
                
    weight_adjustments = await recommend_weight_adjustments(db, days=days)
    
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "global_error_summary": global_error,
        "by_provider": [s for s in by_provider if s.get("confidence") != "low"],
        "by_model": [s for s in by_model if s.get("confidence") != "low"],
        "recommended_cost_multipliers": multipliers,
        "recommended_weight_adjustments": weight_adjustments,
        "warnings": ["Insufficient samples for some providers/models"] if any(s.get("confidence") == "low" for s in by_provider) else [],
        "mode": "recommend_only"
    }
