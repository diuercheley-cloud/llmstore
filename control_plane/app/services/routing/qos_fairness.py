import logging
from datetime import timedelta
from typing import Any, Dict, List

import numpy as np
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_qos_tier import CommercialQoSTier
from app.models.commercial.commercial_queue_metric import CommercialQueueMetric
from app.models.core.generation_job import GenerationJob
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class CommercialQoSFairnessService:
    @staticmethod
    async def collect_queue_metrics(db: AsyncSession, redis: Any) -> List[CommercialQueueMetric]:
        settings = get_settings()
        now = utc_now()
        interval_start = now - timedelta(seconds=settings.commercial_qos_fairness_collection_interval_seconds)
        
        # 1. Get tiers
        result = await db.execute(select(CommercialQoSTier.name))
        tiers = [r[0] for r in result.all()]
        if not tiers:
            tiers = ["Free", "Basic", "Pro", "Premium", "Enterprise"]

        metrics_to_save = []

        for tier in tiers:
            # Current queue depth for this tier (approximate if using same redis key, 
            # but we can query GenerationJob with status='queued')
            depth_stmt = select(func.count()).select_from(GenerationJob).where(
                and_(GenerationJob.status == "queued", GenerationJob.qos_tier == tier)
            )
            depth_result = await db.execute(depth_stmt)
            queue_depth = depth_result.scalar_one()

            # Stats for jobs processed in the last interval
            stats_stmt = select(
                func.avg(GenerationJob.queue_wait_ms),
                func.count(),
                func.max(GenerationJob.queue_wait_ms)
            ).where(
                and_(
                    GenerationJob.qos_tier == tier,
                    GenerationJob.dequeued_at >= interval_start
                )
            )
            stats_result = await db.execute(stats_stmt)
            avg_wait, jobs_processed, max_wait = stats_result.one()
            
            # P95 wait (more complex in SQL, but we can do it if needed or approximate)
            p95_stmt = select(GenerationJob.queue_wait_ms).where(
                and_(
                    GenerationJob.qos_tier == tier,
                    GenerationJob.dequeued_at >= interval_start
                )
            ).order_by(GenerationJob.queue_wait_ms)
            p95_result = await db.execute(p95_stmt)
            waits = [r[0] for r in p95_result.all() if r[0] is not None]
            p95_wait = int(np.percentile(waits, 95)) if waits else 0

            # Throttled jobs
            throttled_stmt = select(func.count()).where(
                and_(
                    GenerationJob.qos_tier == tier,
                    GenerationJob.rate_limit_status == "throttled",
                    GenerationJob.created_at >= interval_start
                )
            )
            throttled_result = await db.execute(throttled_stmt)
            jobs_throttled = throttled_result.scalar_one()

            # Starvation: jobs waiting > threshold
            starvation_threshold_ms = settings.commercial_qos_starvation_threshold_seconds * 1000
            starvation_stmt = select(func.count()).where(
                and_(
                    GenerationJob.status == "queued",
                    GenerationJob.qos_tier == tier,
                    (func.extract('epoch', now) - func.extract('epoch', GenerationJob.queued_at)) * 1000 > starvation_threshold_ms
                )
            )
            starvation_result = await db.execute(starvation_stmt)
            starvation_count = starvation_result.scalar_one()

            # SLA Violations: queue wait > target_latency_ms
            # Get tier info for SLA
            tier_info_stmt = select(CommercialQoSTier).where(CommercialQoSTier.name == tier)
            tier_info_result = await db.execute(tier_info_stmt)
            tier_obj = tier_info_result.scalar_one_or_none()
            
            sla_violations = 0
            if tier_obj:
                sla_stmt = select(func.count()).where(
                    and_(
                        GenerationJob.qos_tier == tier,
                        GenerationJob.dequeued_at >= interval_start,
                        GenerationJob.queue_wait_ms > tier_obj.target_latency_ms
                    )
                )
                sla_result = await db.execute(sla_stmt)
                sla_violations = sla_result.scalar_one()

            metric = CommercialQueueMetric(
                timestamp=now,
                qos_tier=tier,
                queue_depth=queue_depth,
                avg_wait_ms=int(avg_wait) if avg_wait else 0,
                p95_wait_ms=p95_wait,
                max_wait_ms=max_wait if max_wait else 0,
                jobs_processed=jobs_processed,
                jobs_throttled=jobs_throttled,
                starvation_count=starvation_count,
                sla_queue_violations=sla_violations
            )
            metrics_to_save.append(metric)
            db.add(metric)
        
        await db.commit()
        return metrics_to_save

    @staticmethod
    def calculate_fairness_index(values: List[float]) -> float:
        """Jain's Fairness Index: (sum x_i)^2 / (n * sum x_i^2)"""
        if not values:
            return 1.0
        n = len(values)
        sum_x = sum(values)
        sum_x_sq = sum(x**2 for x in values)
        if sum_x_sq == 0:
            return 1.0
        return (sum_x**2) / (n * sum_x_sq)

    @staticmethod
    async def summarize_fairness(db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        now = utc_now()
        since = now - timedelta(hours=hours)
        
        # Get latest metrics
        stmt = select(CommercialQueueMetric).where(CommercialQueueMetric.timestamp >= since).order_by(CommercialQueueMetric.timestamp.desc())
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        
        if not metrics:
            return {"fairness_index": 1.0, "status": "no_data"}

        # Calculate Fairness Index based on relative wait times normalized by priority
        # Higher priority tiers should have lower wait times.
        # Let x_i = (1 / wait_i) * priority_i
        
        tier_stats = {}
        for m in metrics:
            if m.qos_tier not in tier_stats:
                tier_stats[m.qos_tier] = []
            if m.avg_wait_ms > 0:
                tier_stats[m.qos_tier].append(m.avg_wait_ms)

        # To calculate Jain index across tiers, we need a single value per tier
        tier_avg_waits = {t: np.mean(v) for t, v in tier_stats.items() if v}
        
        # Normalize by tier priority
        tier_objs_stmt = select(CommercialQoSTier.name, CommercialQoSTier.priority)
        tier_objs_result = await db.execute(tier_objs_stmt)
        tier_priorities = {r[0]: r[1] for r in tier_objs_result.all()}
        
        fairness_values = []
        for tier, wait in tier_avg_waits.items():
            priority = tier_priorities.get(tier, 10)
            # Share = 1 / (wait / priority) = priority / wait
            # If wait is 0, we'll use a small value to avoid div by zero
            share = priority / max(wait, 1)
            fairness_values.append(share)
            
        fairness_index = CommercialQoSFairnessService.calculate_fairness_index(fairness_values)
        
        return {
            "fairness_index": fairness_index,
            "tier_waits": tier_avg_waits,
            "starvation_total": sum(m.starvation_count for m in metrics),
            "sla_violations_total": sum(m.sla_queue_violations for m in metrics),
            "period_hours": hours
        }

    @staticmethod
    async def detect_starvation(db: AsyncSession) -> List[Dict[str, Any]]:
        settings = get_settings()
        now = utc_now()
        threshold_ms = settings.commercial_qos_starvation_threshold_seconds * 1000
        
        stmt = select(GenerationJob).where(
            and_(
                GenerationJob.status == "queued",
                (func.extract('epoch', now) - func.extract('epoch', GenerationJob.queued_at)) * 1000 > threshold_ms
            )
        )
        result = await db.execute(stmt)
        starving_jobs = result.scalars().all()
        
        return [
            {
                "job_id": job.id,
                "qos_tier": job.qos_tier,
                "wait_seconds": (now - job.queued_at).total_seconds(),
                "priority": job.priority
            }
            for job in starving_jobs
        ]

    @staticmethod
    async def detect_priority_inversion(db: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Detect cases where a job was dequeued while a higher priority job was already waiting.
        """
        # This is a bit expensive to detect strictly. 
        # A simpler way is to look for jobs dequeued in the last hour and check if any 
        # job with higher priority was queued before its dequeue time and still hasn't been dequeued or was dequeued later.
        
        now = utc_now()
        since = now - timedelta(hours=1)
        
        # Jobs dequeued recently
        stmt = select(GenerationJob).where(
            and_(
                GenerationJob.dequeued_at >= since,
                GenerationJob.qos_tier != None
            )
        ).order_by(GenerationJob.dequeued_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        dequeued_jobs = result.scalars().all()
        
        inversions = []
        for job in dequeued_jobs:
            # Check if there were jobs with HIGHER priority (lower score/higher priority value)
            # that were queued BEFORE this job was dequeued, but processed AFTER or still waiting.
            # In our system, higher priority value means higher priority.
            
            inversion_stmt = select(GenerationJob).where(
                and_(
                    GenerationJob.priority > job.priority,
                    GenerationJob.queued_at < job.dequeued_at,
                    (GenerationJob.dequeued_at > job.dequeued_at) | (GenerationJob.status == "queued")
                )
            ).limit(1)
            
            inv_result = await db.execute(inversion_stmt)
            inv_job = inv_result.scalar_one_or_none()
            
            if inv_job:
                inversions.append({
                    "job_id": job.id,
                    "job_priority": job.priority,
                    "job_dequeued_at": job.dequeued_at,
                    "blocked_priority_job_id": inv_job.id,
                    "blocked_priority": inv_job.priority,
                    "blocked_queued_at": inv_job.queued_at
                })
                
        return inversions
