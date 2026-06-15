import time
import uuid

import pytest
from app.services.routing.qos_priority_queue import QoSPriorityQueue


@pytest.mark.asyncio
async def test_qos_priority_queue_ordering(redis_client):
    pq = QoSPriorityQueue(redis_client)

    # Clear queue
    await redis_client.delete(pq.QUEUE_KEY)

    job_free = uuid.uuid4()
    job_enterprise = uuid.uuid4()
    job_premium = uuid.uuid4()

    now_ms = int(time.time() * 1000)

    # Enqueue in "wrong" order
    await pq.enqueue(job_free, priority_weight=100, created_at_ms=now_ms)
    await pq.enqueue(job_enterprise, priority_weight=500, created_at_ms=now_ms + 10)
    await pq.enqueue(job_premium, priority_weight=400, created_at_ms=now_ms + 5)

    # Dequeue should be: Enterprise -> Premium -> Free
    assert await pq.dequeue() == job_enterprise
    assert await pq.dequeue() == job_premium
    assert await pq.dequeue() == job_free
    assert await pq.dequeue() is None


@pytest.mark.asyncio
async def test_qos_priority_queue_fifo_within_tier(redis_client):
    pq = QoSPriorityQueue(redis_client)
    await redis_client.delete(pq.QUEUE_KEY)

    job1 = uuid.uuid4()
    job2 = uuid.uuid4()

    now_ms = int(time.time() * 1000)

    # Same priority, different time
    await pq.enqueue(job1, priority_weight=300, created_at_ms=now_ms)
    await pq.enqueue(job2, priority_weight=300, created_at_ms=now_ms + 10)

    assert await pq.dequeue() == job1
    assert await pq.dequeue() == job2


@pytest.mark.asyncio
async def test_qos_priority_queue_aging(redis_client, settings, monkeypatch):
    pq = QoSPriorityQueue(redis_client)
    await redis_client.delete(pq.QUEUE_KEY)
    await redis_client.delete("qos_queue:last_aging_ts")

    settings.commercial_qos_queue_aging_seconds = 1  # 1 second for test

    current_time = 1000.0

    def fake_time():
        return current_time

    monkeypatch.setattr(time, "time", fake_time)

    job_low = uuid.uuid4()
    job_high = uuid.uuid4()

    # High priority enqueued later
    await pq.enqueue(job_low, priority_weight=100, created_at_ms=1000)
    await pq.enqueue(job_high, priority_weight=500, created_at_ms=2000)

    # Before aging: High -> Low
    assert await pq.peek() == job_high

    # Set the initial last_aging_ts in redis
    await redis_client.set("qos_queue:last_aging_ts", str(current_time))

    # Advance time by 1.1s
    current_time = 1001.1

    score_before = await redis_client.zscore(pq.QUEUE_KEY, str(job_low))
    await pq.apply_aging()
    score_after = await redis_client.zscore(pq.QUEUE_KEY, str(job_low))

    assert score_after < score_before
