# Owner: commercial-ops
from __future__ import annotations

import logging
import uuid
from typing import Any, List

from app.db.redis import get_redis
from app.db.session import get_db_session
from app.models.commercial_qos_tier import CommercialQoSTier
from app.schemas.routing import (
    CommercialQoSChargebackSummary,
    CommercialQoSFairnessSummary,
    CommercialQoSSimulateRequest,
    CommercialQoSSimulateResponse,
    CommercialQoSTierCreate,
    CommercialQoSTierRead,
    CommercialQoSTierUpdate,
)
from app.services.auth import require_admin as get_admin_user
from app.services.routing.commercial_qos import CommercialQoSService
from app.services.routing.commercial_ranker import rank_commercial_routes
from app.services.routing.qos_chargeback import CommercialQoSChargebackService
from app.services.routing.qos_fairness import CommercialQoSFairnessService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/routing/qos", tags=["Commercial QoS"])

@router.get("/fairness/overview", response_model=CommercialQoSFairnessSummary)
async def get_fairness_overview(
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Returns an overview of queue fairness, including Jain's index and wait distribution.
    """
    return await CommercialQoSFairnessService.summarize_fairness(db, hours)

@router.get("/fairness/starvation")
async def get_starvation_report(
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Detects jobs that are currently starving in the queue.
    """
    return await CommercialQoSFairnessService.detect_starvation(db)

@router.get("/fairness/inversions")
async def get_priority_inversions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Detects recent cases of priority inversion.
    """
    return await CommercialQoSFairnessService.detect_priority_inversion(db, limit)

@router.post("/fairness/collect")
async def collect_fairness_metrics(
    db: AsyncSession = Depends(get_db_session),
    redis = Depends(get_redis),
    _admin = Depends(get_admin_user)
):
    """
    Manually triggers a collection of queue metrics.
    """
    metrics = await CommercialQoSFairnessService.collect_queue_metrics(db, redis)
    return {"collected_count": len(metrics)}

@router.get("/chargeback/overview", response_model=CommercialQoSChargebackSummary)
async def get_chargeback_overview(
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Returns an overview of operational chargeback by tier and client.
    """
    return await CommercialQoSChargebackService.summarize_chargeback(db, hours)

@router.post("/chargeback/calculate")
async def calculate_chargeback(
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Manually triggers chargeback calculation for the specified period.
    """
    cbs = await CommercialQoSChargebackService.calculate_chargeback(db, hours)
    return {"calculated_count": len(cbs)}

@router.get("/chargeback/export")
async def export_chargeback(
    format: str = "json",
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    _admin = Depends(get_admin_user)
):
    """
    Exports chargeback data in JSON or CSV format.
    """
    data = await CommercialQoSChargebackService.summarize_chargeback(db, hours)
    
    if format == "csv":
        import csv
        import io

        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Entity Type", "Entity ID", "Amount BRL"])
        
        for tier, amount in data.get("by_tier", {}).items():
            writer.writerow(["Tier", tier, amount])
        for client, amount in data.get("by_client", {}).items():
            writer.writerow(["Client", client, amount])
            
        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=chargeback_{hours}h.csv"}
        )
        
    return data

@router.get("/tiers", response_model=List[CommercialQoSTierRead])
async def list_qos_tiers(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Lists all QoS tiers.
    """
    return await CommercialQoSService.get_all_tiers(db)

@router.post("/tiers", response_model=CommercialQoSTierRead, status_code=201)
async def create_qos_tier(
    req: CommercialQoSTierCreate,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Creates a new QoS tier.
    """
    # Check if name already exists
    existing = await CommercialQoSService.get_tier_by_name(db, req.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"QoS Tier with name '{req.name}' already exists")
        
    tier = CommercialQoSTier(**req.model_dump())
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return tier

@router.patch("/tiers/{tier_id}", response_model=CommercialQoSTierRead)
async def update_qos_tier(
    tier_id: uuid.UUID,
    req: CommercialQoSTierUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Updates an existing QoS tier.
    """
    tier = await db.get(CommercialQoSTier, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="QoS Tier not found")
        
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tier, key, value)
        
    await db.commit()
    await db.refresh(tier)
    return tier

@router.delete("/tiers/{tier_id}")
async def delete_qos_tier(
    tier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Deletes a QoS tier.
    """
    tier = await db.get(CommercialQoSTier, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="QoS Tier not found")
        
    await db.delete(tier)
    await db.commit()
    return {"status": "success"}

@router.get("/overview")
async def get_qos_overview(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns an overview of QoS tiers and their status.
    """
    tiers = await CommercialQoSService.get_all_tiers(db)
    # In a real system, we would join with routing events to get pass rates
    return {
        "total_tiers": len(tiers),
        "enabled_tiers": [t.name for t in tiers if t.enabled],
        "timestamp": uuid.uuid4(), # placeholder
    }

from app.core.config import get_settings
from app.db.session import redis_client
from app.models.generation_job import GenerationJob
from app.services.routing.qos_priority_queue import QoSPriorityQueue
from app.services.routing.qos_rate_limiter import QoSRateLimiter


@router.get("/queue/overview")
async def get_queue_overview(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns an overview of the QoS priority queue.
    """
    pq = QoSPriorityQueue(redis_client)
    stats = await pq.get_stats()
    
    # Get depth per tier by querying DB for 'queued' jobs grouped by qos_tier
    from sqlalchemy import func
    tier_depths = await db.execute(
        select(GenerationJob.qos_tier, func.count(GenerationJob.id))
        .where(GenerationJob.status == "queued")
        .group_by(GenerationJob.qos_tier)
    )
    depth_by_tier = {tier: count for tier, count in tier_depths.all()}
    
    # Get oldest job wait time
    oldest_job = await db.execute(
        select(GenerationJob)
        .where(GenerationJob.status == "queued")
        .order_by(GenerationJob.queued_at.asc())
        .limit(1)
    )
    oldest = oldest_job.scalar_one_or_none()
    max_wait_ms = 0
    if oldest and oldest.queued_at:
        from app.core.time import utc_now
        max_wait_ms = int((utc_now() - oldest.queued_at).total_seconds() * 1000)

    settings = get_settings()
    return {
        "depth": stats.get("depth", 0),
        "depth_by_tier": depth_by_tier,
        "max_wait_ms": max_wait_ms,
        "mode": settings.commercial_qos_priority_queue_mode,
        "enabled": settings.commercial_qos_priority_queue_enabled,
        "shadow_mode_active": settings.commercial_qos_priority_queue_mode == "shadow"
    }

@router.get("/queue/jobs")
async def list_queue_jobs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Lists jobs currently in the priority queue.
    """
    jobs = await db.execute(
        select(GenerationJob)
        .where(GenerationJob.status == "queued")
        .order_by(GenerationJob.effective_priority.asc())
        .limit(limit)
    )
    from app.services.generation_jobs import serialize_job
    return [serialize_job(j) for j in jobs.scalars().all()]

@router.get("/rate-limits/overview")
async def get_rate_limits_overview(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns an overview of rate limiting status.
    """
    settings = get_settings()
    # In a real system, we'd fetch top throttled clients from Redis
    return {
        "enabled": settings.commercial_qos_rate_limiting_enabled,
        "mode": settings.commercial_qos_rate_limit_mode,
        "tiers": {
            "Free": settings.commercial_qos_free_rpm,
            "Basic": settings.commercial_qos_basic_rpm,
            "Pro": settings.commercial_qos_pro_rpm,
            "Premium": settings.commercial_qos_premium_rpm,
            "Enterprise": settings.commercial_qos_enterprise_rpm,
        }
    }

@router.post("/rate-limits/simulate")
async def simulate_rate_limit(
    client_id: uuid.UUID,
    qos_tier: str,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Simulates a rate limit check for a client.
    """
    rl = QoSRateLimiter(redis_client)
    allowed, status, reason = await rl.check_rate_limit(client_id, qos_tier, "test-model")
    current_rpm = await rl.get_current_rpm(client_id)
    
    return {
        "allowed": allowed,
        "status": status,
        "reason": reason,
        "current_rpm": current_rpm,
        "tier": qos_tier
    }

@router.post("/simulate", response_model=CommercialQoSSimulateResponse)
async def simulate_qos_routing(
    req: CommercialQoSSimulateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Simulates routing decision for a specific tier/plan.
    """
    tier = await CommercialQoSService.resolve_qos_tier(db, req.client_id, req.plan)
    
    # Mock candidates
    candidates = [
        {"provider": "local", "model": "gemma", "quality": 70},
        {"provider": "openai", "model": "gpt-4", "quality": 95},
        {"provider": "anthropic", "model": "claude-3", "quality": 98},
        {"provider": "deepseek", "model": "deepseek-v2", "quality": 88},
    ]
    
    ranked, rejected, _ = rank_commercial_routes(
        candidates=candidates,
        client_plan=req.plan or "basic",
        task_type=req.task_type,
        estimated_input_tokens=req.estimated_tokens // 2,
        estimated_output_tokens=req.estimated_tokens // 2,
        client_id=str(req.client_id) if req.client_id else None,
        qos_tier=tier, # We need to update rank_commercial_routes to support this
    )
    
    selected = ranked[0] if ranked else None
    sla_pass = True
    degradation_path = None
    
    if not selected and rejected:
        selected, degradation_path = CommercialQoSService.choose_degradation_path(tier, ranked, rejected)
        sla_pass = False

    return CommercialQoSSimulateResponse(
        tier=tier.name,
        selected_route=selected,
        ranked_routes=ranked,
        rejected_routes=rejected,
        degradation_path=degradation_path,
        sla_pass=sla_pass,
        warnings=[]
    )
