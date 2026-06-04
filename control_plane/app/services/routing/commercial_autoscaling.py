import logging
import uuid
from typing import List, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_capacity import (
    CommercialAutoscalingRecommendation,
    CommercialCapacityForecast,
)
from app.services.routing.commercial_infra_simulation import (
    simulate_reroute,
    simulate_scale_down,
    simulate_scale_up,
)
from app.services.routing.commercial_safety_gates import validate_simulation_against_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def generate_autoscaling_recommendations(db: AsyncSession, cluster_id: str) -> List[CommercialAutoscalingRecommendation]:
    """
    Analyzes recent forecasts and snapshots to generate recommendations.
    """
    settings = get_settings()
    if not settings.commercial_capacity_planning_enabled:
        return []

    # 1. Fetch latest forecasts
    stmt = select(CommercialCapacityForecast).where(
        CommercialCapacityForecast.cluster_id == cluster_id
    ).order_by(CommercialCapacityForecast.created_at.desc()).limit(10)
    
    result = await db.execute(stmt)
    forecasts = result.scalars().all()
    
    recommendations = []
    
    for forecast in forecasts:
        rec = None
        if forecast.recommended_action == "scale_up" and forecast.confidence > 0.7:
            rec = await recommend_scale_up(db, forecast)
        elif forecast.predicted_sla_violation_rate > settings.commercial_sla_risk_alert_percent:
            rec = await recommend_qos_throttling(db, forecast)
            
        if rec:
            recommendations.append(rec)
            # Phase 21.1: Trigger simulation and safety gates
            if settings.commercial_infra_simulation_enabled:
                simulation = await run_simulation_for_recommendation(db, rec)
                if simulation:
                    status, reason = await validate_simulation_against_policy(db, simulation)
                    simulation.safety_gate_status = status
                    logger.info(f"Recommendation {rec.id} simulated. Status: {status}. Reason: {reason}")

    await db.commit()
    return recommendations

async def run_simulation_for_recommendation(db: AsyncSession, rec: CommercialAutoscalingRecommendation):
    """
    Helper to run a simulation for a generated recommendation.
    """
    if rec.recommendation_type == "scale_up":
        return await simulate_scale_up(db, rec.target_scope, rec.target_identifier, {"nodes": 1})
    elif rec.recommendation_type == "scale_down":
        return await simulate_scale_down(db, rec.target_scope, rec.target_identifier, {"nodes": 1})
    elif rec.recommendation_type == "reroute":
        return await simulate_reroute(db, rec.target_scope, rec.target_identifier, {"traffic_percent": 10})
    return None

async def recommend_scale_up(db: AsyncSession, forecast: CommercialCapacityForecast) -> Optional[CommercialAutoscalingRecommendation]:
    rec = CommercialAutoscalingRecommendation(
        id=uuid.uuid4(),
        cluster_id=forecast.cluster_id,
        recommendation_type="scale_up",
        target_scope="provider" if forecast.provider else "cluster",
        target_identifier=forecast.provider or forecast.cluster_id,
        reason=f"Predicted RPM growth of {forecast.predicted_rpm:.2f} exceeds capacity. SLA risk is {forecast.predicted_sla_violation_rate:.2f}%.",
        predicted_sla_risk=forecast.predicted_sla_violation_rate,
        estimated_cost_impact_brl=10.0, # Placeholder
        estimated_margin_impact_brl=-2.0, # Placeholder
        confidence=forecast.confidence,
        dry_run_only=True,
        created_at=utc_now()
    )
    db.add(rec)
    return rec

async def recommend_scale_down(db: AsyncSession, forecast: CommercialCapacityForecast) -> Optional[CommercialAutoscalingRecommendation]:
    # Placeholder
    return None

async def recommend_reroute(db: AsyncSession, forecast: CommercialCapacityForecast) -> Optional[CommercialAutoscalingRecommendation]:
    # Placeholder
    return None

async def recommend_cache_expansion(db: AsyncSession, forecast: CommercialCapacityForecast) -> Optional[CommercialAutoscalingRecommendation]:
    # Placeholder
    return None

async def recommend_qos_throttling(db: AsyncSession, forecast: CommercialCapacityForecast) -> Optional[CommercialAutoscalingRecommendation]:
    target = forecast.qos_tier or "Free"
    rec = CommercialAutoscalingRecommendation(
        id=uuid.uuid4(),
        cluster_id=forecast.cluster_id,
        recommendation_type="throttle",
        target_scope="qos_tier",
        target_identifier=target,
        reason=f"High SLA risk ({forecast.predicted_sla_violation_rate:.2f}%) predicted for {target} tier. Throttling recommended to protect Premium tiers.",
        predicted_sla_risk=forecast.predicted_sla_violation_rate,
        estimated_cost_impact_brl=0.0,
        estimated_margin_impact_brl=1.0, # Throttling saves cost
        confidence=forecast.confidence,
        dry_run_only=True,
        created_at=utc_now()
    )
    db.add(rec)
    return rec
