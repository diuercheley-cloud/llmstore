import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_capacity import CommercialCapacitySnapshot
from app.models.commercial_routing_event import CommercialRoutingEvent
from app.models.commercial_node_heartbeat import CommercialNodeHeartbeat

logger = logging.getLogger(__name__)

async def capture_capacity_snapshot(db: AsyncSession, cluster_id: Optional[str] = None) -> List[CommercialCapacitySnapshot]:
    """
    Captures a snapshot of the current cluster capacity based on recent events and node status.
    """
    settings = get_settings()
    if not settings.commercial_capacity_planning_enabled:
        return []

    from sqlalchemy import case as sa_case

    target_cluster = cluster_id or settings.cluster_id
    now = utc_now()
    lookback_window = timedelta(minutes=5)
    start_time = now - lookback_window

    # 1. Gather aggregate metrics from Routing Events
    # We aggregate by provider, model, qos_tier
    metrics_stmt = select(
        CommercialRoutingEvent.selected_provider,
        CommercialRoutingEvent.selected_model,
        CommercialRoutingEvent.qos_tier,
        func.count(CommercialRoutingEvent.id).label("total_requests"),
        func.avg(CommercialRoutingEvent.estimated_margin_percent).label("avg_margin"), # Not in snapshot but useful
        func.sum(sa_case((CommercialRoutingEvent.sla_pass == False, 1), else_=0)).label("sla_violations"),
        func.sum(sa_case((CommercialRoutingEvent.fallback_used == True, 1), else_=0)).label("fallbacks"),
        func.sum(sa_case((CommercialRoutingEvent.blocked == True, 1), else_=0)).label("blocks"),
    ).where(
        and_(
            CommercialRoutingEvent.created_at >= start_time,
            # If we had a cluster_id in CommercialRoutingEvent we would filter here
            # For now we assume the DB is cluster-scoped or shared
        )
    ).group_by(
        CommercialRoutingEvent.selected_provider,
        CommercialRoutingEvent.selected_model,
        CommercialRoutingEvent.qos_tier
    )

    result = await db.execute(metrics_stmt)
    rows = result.all()

    snapshots = []
    
    # Also gather node metrics for utilization
    node_stmt = select(CommercialNodeHeartbeat).where(
        and_(
            CommercialNodeHeartbeat.last_seen_at >= now - timedelta(seconds=settings.commercial_node_offline_after_seconds),
            # Filter by cluster if possible
        )
    )
    node_result = await db.execute(node_stmt)
    nodes = node_result.scalars().all()
    
    # Simplify for Phase 21: One snapshot per (cluster, provider, model, qos_tier)
    # Plus a global cluster snapshot
    
    for row in rows:
        provider, model, qos_tier, total_reqs, avg_margin, sla_v, fallbacks, blocks = row
        
        rpm = total_reqs / (lookback_window.total_seconds() / 60.0)
        sla_rate = (sla_v / total_reqs * 100.0) if total_reqs > 0 else 0.0
        fallback_rate = (fallbacks / total_reqs * 100.0) if total_reqs > 0 else 0.0
        block_rate = (blocks / total_reqs * 100.0) if total_reqs > 0 else 0.0
        
        # Estimate concurrency and latency from events if we had timing info
        # For Phase 21 we'll use simplified heuristics if timing is missing
        
        snapshot = CommercialCapacitySnapshot(
            id=uuid.uuid4(),
            cluster_id=target_cluster,
            provider=provider,
            model=model,
            qos_tier=qos_tier,
            timestamp=now,
            requests_per_minute=rpm,
            concurrent_requests=int(rpm / 10), # Heuristic
            avg_latency_ms=2000.0, # Placeholder
            p95_latency_ms=5000.0, # Placeholder
            queue_depth=0, # Placeholder
            sla_violation_rate=sla_rate,
            fallback_rate=fallback_rate,
            block_rate=block_rate,
            created_at=now
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    # Global cluster snapshot
    if nodes:
        total_cpu = sum([n.metadata_json.get("cpu_utilization", 0.0) for n in nodes if n.metadata_json]) / len(nodes)
        total_mem = sum([n.metadata_json.get("memory_utilization", 0.0) for n in nodes if n.metadata_json]) / len(nodes)
        total_gpu = sum([n.metadata_json.get("gpu_utilization", 0.0) for n in nodes if n.metadata_json]) / len(nodes)
        
        cluster_snapshot = CommercialCapacitySnapshot(
            id=uuid.uuid4(),
            cluster_id=target_cluster,
            timestamp=now,
            cpu_utilization=total_cpu,
            memory_utilization=total_mem,
            gpu_utilization=total_gpu,
            created_at=now
        )
        db.add(cluster_snapshot)
        snapshots.append(cluster_snapshot)

    await db.commit()
    return snapshots

async def summarize_cluster_capacity(db: AsyncSession, cluster_id: str, window_minutes: int = 60) -> Dict[str, Any]:
    start_time = utc_now() - timedelta(minutes=window_minutes)
    stmt = select(CommercialCapacitySnapshot).where(
        and_(
            CommercialCapacitySnapshot.cluster_id == cluster_id,
            CommercialCapacitySnapshot.timestamp >= start_time,
            CommercialCapacitySnapshot.provider == None # Global cluster snapshots
        )
    ).order_by(CommercialCapacitySnapshot.timestamp.desc())
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    if not snapshots:
        return {"cluster_id": cluster_id, "status": "no_data"}
        
    latest = snapshots[0]
    return {
        "cluster_id": cluster_id,
        "timestamp": latest.timestamp,
        "cpu": latest.cpu_utilization,
        "memory": latest.memory_utilization,
        "gpu": latest.gpu_utilization,
        "snapshot_count": len(snapshots)
    }

async def summarize_provider_capacity(db: AsyncSession, cluster_id: str, provider: str) -> Dict[str, Any]:
    # Similar to cluster but filtered by provider
    pass

async def summarize_qos_capacity(db: AsyncSession, cluster_id: str, qos_tier: str) -> Dict[str, Any]:
    # Similar to cluster but filtered by qos_tier
    pass

async def cleanup_old_snapshots(db: AsyncSession) -> int:
    settings = get_settings()
    retention_days = settings.commercial_capacity_retention_days
    cutoff = utc_now() - timedelta(days=retention_days)
    
    stmt = delete(CommercialCapacitySnapshot).where(CommercialCapacitySnapshot.timestamp < cutoff)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
