import uuid
from datetime import timedelta

import pytest
from app.core.time import utc_now
from app.models.core.generation_job import GenerationJob
from app.services.routing.qos_fairness import CommercialQoSFairnessService


@pytest.mark.asyncio
async def test_calculate_fairness_index():
    service = CommercialQoSFairnessService()

    # Perfectly fair: [1, 1, 1] -> (3)^2 / (3 * (1+1+1)) = 9 / 9 = 1.0
    assert service.calculate_fairness_index([1.0, 1.0, 1.0]) == 1.0

    # Unfair: [1, 0] -> (1)^2 / (2 * (1+0)) = 1 / 2 = 0.5
    assert service.calculate_fairness_index([1.0, 0.0]) == 0.5

    # Very unfair: [10, 1, 1] -> (12)^2 / (3 * (100+1+1)) = 144 / (3 * 102) = 144 / 306 ~= 0.47
    index = service.calculate_fairness_index([10.0, 1.0, 1.0])
    assert 0.46 < index < 0.48


@pytest.mark.asyncio
async def test_collect_queue_metrics(session, redis_client):
    service = CommercialQoSFairnessService()
    now = utc_now()

    # Create mock client and jobs
    client_id = uuid.uuid4()

    # Job processed in last interval
    job1 = GenerationJob(
        id=uuid.uuid4(),
        client_id=client_id,
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="completed",
        qos_tier="Pro",
        queue_wait_ms=500,
        queued_at=now - timedelta(seconds=10),
        dequeued_at=now - timedelta(seconds=5),
        completed_at=now - timedelta(seconds=2),
        priority=300,
        request_json="{}",
    )

    # Job still in queue
    job2 = GenerationJob(
        id=uuid.uuid4(),
        client_id=client_id,
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="queued",
        qos_tier="Pro",
        queued_at=now - timedelta(seconds=20),
        priority=300,
        request_json="{}",
    )

    session.add(job1)
    session.add(job2)
    await session.commit()

    metrics = await service.collect_queue_metrics(session, redis_client)

    # Find Pro tier metric
    pro_metric = next((m for m in metrics if m.qos_tier == "Pro"), None)
    assert pro_metric is not None
    assert pro_metric.queue_depth == 1
    assert pro_metric.jobs_processed == 1
    assert pro_metric.avg_wait_ms == 500


@pytest.mark.asyncio
async def test_detect_starvation(session, settings):
    service = CommercialQoSFairnessService()
    now = utc_now()
    settings.commercial_qos_starvation_threshold_seconds = 10

    # Starving job
    job = GenerationJob(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="queued",
        qos_tier="Free",
        queued_at=now - timedelta(seconds=15),
        priority=100,
        request_json="{}",
    )
    session.add(job)
    await session.commit()

    starving = await service.detect_starvation(session)
    assert len(starving) == 1
    assert starving[0]["qos_tier"] == "Free"


@pytest.mark.asyncio
async def test_detect_priority_inversion(session):
    service = CommercialQoSFairnessService()
    now = utc_now()

    # Job dequeued with low priority
    job_low = GenerationJob(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="completed",
        qos_tier="Free",
        priority=100,
        queued_at=now - timedelta(seconds=20),
        dequeued_at=now - timedelta(seconds=10),
        request_json="{}",
    )

    # Higher priority job queued BEFORE job_low was dequeued, but still queued (or dequeued later)
    job_high = GenerationJob(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        requested_model="gpt-3.5-turbo",
        resolved_model="gpt-3.5-turbo",
        status="queued",
        qos_tier="Enterprise",
        priority=500,
        queued_at=now - timedelta(seconds=15),
        request_json="{}",
    )

    session.add(job_low)
    session.add(job_high)
    await session.commit()

    inversions = await service.detect_priority_inversion(session)
    assert len(inversions) > 0
    assert inversions[0]["job_id"] == job_low.id
    assert inversions[0]["blocked_priority"] == 500
