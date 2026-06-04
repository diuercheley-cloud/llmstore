import uuid
from datetime import timedelta

import pytest
from app.core.time import utc_now
from app.models.generation_job import GenerationJob
from app.services.routing.qos_chargeback import CommercialQoSChargebackService


@pytest.mark.asyncio
async def test_calculate_chargeback_logic(session, settings):
    service = CommercialQoSChargebackService()
    now = utc_now()
    settings.commercial_qos_priority_slot_cost_brl_per_second = 0.001
    
    client_id = uuid.uuid4()
    
    # 1. Premium Job (high priority)
    job1 = GenerationJob(
        id=uuid.uuid4(),
        client_id=client_id,
        requested_model="gpt-4",
        resolved_model="gpt-4",
        status="completed",
        qos_tier="Premium",
        priority=400, # 4x base
        queued_at=now - timedelta(seconds=60),
        started_at=now - timedelta(seconds=55),
        completed_at=now - timedelta(seconds=45), # 10s compute
        queue_wait_ms=5000,
        request_json="{}"
    )
    
    # 2. Free Job (low priority) during critical moment
    job2 = GenerationJob(
        id=uuid.uuid4(),
        client_id=client_id,
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="completed",
        qos_tier="Free",
        priority=100, # 1x base
        queued_at=now - timedelta(seconds=70),
        started_at=now - timedelta(seconds=65),
        completed_at=now - timedelta(seconds=60), # 5s compute
        queue_wait_ms=5000,
        request_json="{}"
    )
    
    # To trigger opportunity cost for job2, we need a high priority job waiting when job2 started.
    # Job1 was queued at now-60s, but Job2 started at now-65s and ended at now-60s.
    # So Job1 was NOT waiting when Job2 started.
    
    # Let's add Job3 (High Priority) waiting while Job2 (Low Priority) is running.
    job3 = GenerationJob(
        id=uuid.uuid4(),
        client_id=client_id,
        requested_model="gpt-4",
        resolved_model="gpt-4",
        status="queued",
        qos_tier="Enterprise",
        priority=500,
        queued_at=now - timedelta(seconds=68), # Queued while Job2 is running (65s to 60s)
        request_json="{}"
    )
    
    session.add(job1)
    session.add(job2)
    session.add(job3)
    await session.commit()
    
    chargebacks = await service.calculate_chargeback(session)
    
    # Find Premium chargeback
    premium_cb = next((c for c in chargebacks if c.qos_tier == "Premium"), None)
    assert premium_cb is not None
    # compute_seconds = 10, priority_weight = 4.0 -> slots = 40
    # internal_cost = 40 * 0.001 = 0.04
    assert float(premium_cb.compute_seconds) == 10.0
    assert float(premium_cb.priority_slots_consumed) == 40.0
    assert float(premium_cb.estimated_internal_cost_brl) == 0.04

    # Find Free chargeback
    free_cb = next((c for c in chargebacks if c.qos_tier == "Free"), None)
    assert free_cb is not None
    assert float(free_cb.compute_seconds) == 5.0
    # Job3 (priority 500) was waiting when Job2 (priority 100) was running.
    # Job2 started at -65s, Job3 queued at -68s. So Job3 was waiting.
    # Job2 ended at -60s. Job3 was waiting throughout Job2's compute (5s).
    # opp_cost = 5s * 0.01 * 1 (high priority job) = 0.05
    assert float(free_cb.estimated_opportunity_cost_brl) > 0

@pytest.mark.asyncio
async def test_summarize_chargeback(session):
    service = CommercialQoSChargebackService()
    now = utc_now()
    
    from app.models.commercial_queue_chargeback import CommercialQueueChargeback
    
    cb1 = CommercialQueueChargeback(
        period_start=now - timedelta(hours=1),
        period_end=now,
        qos_tier="Pro",
        chargeback_amount_brl=1.5,
        compute_seconds=100,
        queue_wait_seconds=10,
        priority_slots_consumed=200
    )
    session.add(cb1)
    await session.commit()
    
    summary = await service.summarize_chargeback(session)
    assert summary["total_chargeback_brl"] == 1.5
    assert summary["by_tier"]["Pro"] == 1.5
