import uuid

import pytest
from app.services.agents.agent_worker import AgentWorkerService
from app.services.agents.tracing import tracing_service
from app.services.batches.redis_queue import RedisAgentQueue


@pytest.mark.asyncio
async def test_redis_queue_basic(fake_redis):
    queue = RedisAgentQueue(fake_redis)
    run_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    # 1. Enqueue
    job_id = await queue.enqueue_job(run_id, agent_id, "tenant-1", priority=10)
    assert job_id is not None
    
    # 2. Dequeue
    job = await queue.dequeue_job("worker-1")
    assert job is not None
    assert job["id"] == job_id
    assert job["priority"] == 10
    
    # 3. Complete
    await queue.complete_job(job_id)
    
    # 4. Should be empty
    job2 = await queue.dequeue_job("worker-1")
    assert job2 is None

def test_tracing_service_init():
    tracer = tracing_service.get_tracer()
    assert tracer is not None
    
    with tracing_service.start_span("test-span"):
        pass # Just verify it doesn't crash

@pytest.mark.asyncio
async def test_worker_drain_status():
    worker = AgentWorkerService(worker_id="test-worker")
    assert not worker.is_draining
    
    worker.drain()
    assert worker.is_draining
