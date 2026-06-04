import logging
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_capacity import CommercialCapacityForecast, CommercialCapacitySnapshot
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def forecast_capacity(
    db: AsyncSession, 
    cluster_id: str, 
    provider: Optional[str] = None, 
    model: Optional[str] = None, 
    qos_tier: Optional[str] = None
) -> Optional[CommercialCapacityForecast]:
    """
    Generates a capacity forecast based on recent snapshots.
    Uses a simple moving average / linear extrapolation for demonstration.
    """
    settings = get_settings()
    window_minutes = settings.commercial_capacity_forecast_window_minutes
    lookback_window = timedelta(hours=6)
    start_time = utc_now() - lookback_window

    filters = [
        CommercialCapacitySnapshot.cluster_id == cluster_id,
        CommercialCapacitySnapshot.timestamp >= start_time
    ]
    if provider:
        filters.append(CommercialCapacitySnapshot.provider == provider)
    else:
        filters.append(CommercialCapacitySnapshot.provider == None)
        
    if model:
        filters.append(CommercialCapacitySnapshot.model == model)
    if qos_tier:
        filters.append(CommercialCapacitySnapshot.qos_tier == qos_tier)

    stmt = select(CommercialCapacitySnapshot).where(and_(*filters)).order_by(CommercialCapacitySnapshot.timestamp.asc())
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    if len(snapshots) < 5:
        return None # Not enough data

    # Simple Moving Average
    avg_rpm = sum(s.requests_per_minute for s in snapshots) / len(snapshots)
    avg_concurrency = sum(s.concurrent_requests for s in snapshots) / len(snapshots)
    avg_latency = sum(s.avg_latency_ms for s in snapshots) / len(snapshots)
    avg_sla_violation = sum(s.sla_violation_rate for s in snapshots) / len(snapshots)
    
    # Simple trend calculation (comparing last 20% vs first 20%)
    split = len(snapshots) // 5
    recent_rpm = sum(s.requests_per_minute for s in snapshots[-split:]) / split
    older_rpm = sum(s.requests_per_minute for s in snapshots[:split]) / split
    
    trend = (recent_rpm - older_rpm) / older_rpm if older_rpm > 0 else 0.0
    
    predicted_rpm = recent_rpm * (1 + trend)
    predicted_concurrency = avg_concurrency * (1 + trend)
    predicted_sla = avg_sla_violation * (1 + max(0, trend * 2)) # Nonlinear risk
    
    # Predict exhaustion if RPM is growing
    exhaustion_at = None
    if trend > 0.05: # Growing more than 5% in lookback window
        # Extremely simplified: assume 1000 RPM is the limit for now
        limit_rpm = 1000.0 
        minutes_to_limit = (limit_rpm - recent_rpm) / (trend * recent_rpm / (lookback_window.total_seconds() / 60)) if trend > 0 else 0
        if 0 < minutes_to_limit < 1440: # Within 24h
            exhaustion_at = utc_now() + timedelta(minutes=minutes_to_limit)

    recommendation = "maintain"
    if trend > 0.2:
        recommendation = "scale_up"
    elif trend < -0.3:
        recommendation = "scale_down"
        
    forecast = CommercialCapacityForecast(
        id=uuid.uuid4(),
        cluster_id=cluster_id,
        provider=provider,
        model=model,
        qos_tier=qos_tier,
        forecast_window_minutes=window_minutes,
        predicted_rpm=predicted_rpm,
        predicted_concurrency=predicted_concurrency,
        predicted_latency_ms=avg_latency,
        predicted_sla_violation_rate=predicted_sla,
        predicted_capacity_exhaustion_at=exhaustion_at,
        recommended_action=recommendation,
        confidence=0.8 if len(snapshots) > 20 else 0.5,
        created_at=utc_now()
    )
    db.add(forecast)
    await db.commit()
    return forecast

async def detect_capacity_anomalies(db: AsyncSession, cluster_id: str) -> List[Dict[str, Any]]:
    """
    Detects sudden spikes or drops in capacity metrics.
    """
    # Placeholder for Phase 21
    return []

async def predict_sla_violation(db: AsyncSession, cluster_id: str) -> bool:
    # Placeholder
    return False
