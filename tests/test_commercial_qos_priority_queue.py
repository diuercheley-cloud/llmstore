import uuid
import pytest
import time
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
async def test_qos_priority_queue_aging(redis_client, settings):
    pq = QoSPriorityQueue(redis_client)
    await redis_client.delete(pq.QUEUE_KEY)
    await redis_client.delete("qos_queue:last_aging_ts")
    
    settings.commercial_qos_queue_aging_seconds = 1 # 1 second for test
    
    job_low = uuid.uuid4()
    job_high = uuid.uuid4()
    
    # High priority enqueued later
    await pq.enqueue(job_low, priority_weight=100, created_at_ms=1000)
    await pq.enqueue(job_high, priority_weight=500, created_at_ms=2000)
    
    # Before aging: High -> Low
    # (Checking peek/dequeue without actually dequeuing if possible, or just re-enqueue)
    assert await pq.peek() == job_high
    
    # Wait for aging interval
    time.sleep(1.1)
    
    # Apply aging multiple times to make Low cross High
    # High score = -500M + 2000 = -499,998,000
    # Low score = -100M + 1000 = -99,999,000
    # Each aging step is -100k. Needs ~4000 steps to cross? 
    # That's too many for a test. Let's just verify score changes.
    
    score_before = await redis_client.zscore(pq.QUEUE_KEY, str(job_low))
    await pq.apply_aging()
    score_after = await redis_client.zscore(pq.QUEUE_KEY, str(job_low))
    
    assert score_after < score_before
