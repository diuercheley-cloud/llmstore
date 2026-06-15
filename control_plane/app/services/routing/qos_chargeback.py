import logging
from datetime import timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_queue_chargeback import CommercialQueueChargeback
from app.models.core.generation_job import GenerationJob
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CommercialQoSChargebackService:
    @staticmethod
    async def calculate_chargeback(
        db: AsyncSession, period_hours: int = 24
    ) -> list[CommercialQueueChargeback]:
        settings = get_settings()
        now = utc_now()
        period_start = now - timedelta(hours=period_hours)

        # Get all completed jobs in the period
        stmt = select(GenerationJob).where(
            and_(GenerationJob.completed_at >= period_start, GenerationJob.qos_tier != None)
        )
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        # Aggregate by tier and client
        aggregates = {}  # key: (tier, client_id, model)

        for job in jobs:
            key = (job.qos_tier, job.client_id, job.resolved_model)
            if key not in aggregates:
                aggregates[key] = {
                    "compute_seconds": 0.0,
                    "queue_wait_seconds": 0.0,
                    "priority_slots_consumed": 0.0,
                    "opportunity_cost": 0.0,
                    "internal_cost": 0.0,
                }

            compute_seconds = 0.0
            if job.started_at and job.completed_at:
                compute_seconds = (job.completed_at - job.started_at).total_seconds()

            queue_wait_seconds = (job.queue_wait_ms or 0) / 1000.0

            # Priority slots: compute time weighted by priority
            # Use priority 100 as base (1.0)
            priority_weight = (job.priority or 100) / 100.0
            slots_consumed = compute_seconds * priority_weight

            # Opportunity cost: if job is low priority and high priority jobs were waiting
            # For simplicity, we'll check if there were jobs with priority > job.priority
            # that were queued before this job started.
            opp_cost = 0.0
            if job.priority < 200:  # Low priority threshold
                # Check for high priority jobs waiting when this one started
                if job.started_at:
                    opp_stmt = select(func.count()).where(
                        and_(
                            GenerationJob.priority >= 200,
                            GenerationJob.queued_at < job.started_at,
                            (GenerationJob.dequeued_at > job.started_at)
                            | (GenerationJob.status == "queued"),
                        )
                    )
                    opp_result = await db.execute(opp_stmt)
                    high_priority_waiting = opp_result.scalar_one()
                    if high_priority_waiting > 0:
                        # Penalty for each high priority job blocked
                        opp_cost = compute_seconds * 0.01 * high_priority_waiting

            aggregates[key]["compute_seconds"] += compute_seconds
            aggregates[key]["queue_wait_seconds"] += queue_wait_seconds
            aggregates[key]["priority_slots_consumed"] += slots_consumed
            aggregates[key]["opportunity_cost"] += opp_cost

            # Internal cost estimate
            base_cost_per_sec = settings.commercial_qos_priority_slot_cost_brl_per_second
            internal_cost = slots_consumed * base_cost_per_sec
            aggregates[key]["internal_cost"] += internal_cost

        chargebacks = []
        for (tier, client_id, model), data in aggregates.items():
            cb = CommercialQueueChargeback(
                period_start=period_start,
                period_end=now,
                qos_tier=tier,
                client_id=client_id,
                model=model,
                compute_seconds=data["compute_seconds"],
                queue_wait_seconds=data["queue_wait_seconds"],
                priority_slots_consumed=data["priority_slots_consumed"],
                estimated_opportunity_cost_brl=data["opportunity_cost"],
                estimated_internal_cost_brl=data["internal_cost"],
                chargeback_amount_brl=data["internal_cost"] + data["opportunity_cost"],
            )
            db.add(cb)
            chargebacks.append(cb)

        await db.commit()
        return chargebacks

    @staticmethod
    async def summarize_chargeback(db: AsyncSession, hours: int = 24) -> dict[str, Any]:
        now = utc_now()
        since = now - timedelta(hours=hours)

        stmt = select(CommercialQueueChargeback).where(
            CommercialQueueChargeback.period_end >= since
        )
        result = await db.execute(stmt)
        cbs = result.scalars().all()

        by_tier = {}
        by_client = {}
        total_amount = 0.0

        for cb in cbs:
            total_amount += float(cb.chargeback_amount_brl)

            if cb.qos_tier not in by_tier:
                by_tier[cb.qos_tier] = 0.0
            by_tier[cb.qos_tier] += float(cb.chargeback_amount_brl)

            client_key = str(cb.client_id) if cb.client_id else "anonymous"
            if client_key not in by_client:
                by_client[client_key] = 0.0
            by_client[client_key] += float(cb.chargeback_amount_brl)

        return {
            "total_chargeback_brl": total_amount,
            "by_tier": by_tier,
            "by_client": by_client,
            "record_count": len(cbs),
            "period_hours": hours,
        }
