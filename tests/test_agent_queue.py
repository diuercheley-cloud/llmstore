import pytest
import uuid
import asyncio
from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_execution import AgentExecutionJob, AgentExecutionDeadLetter
from app.services.agents.agent_queue import AgentQueueManager
from app.services.agents.agent_worker import AgentWorkerService
from app.core.time import utc_now

@pytest.fixture(autouse=True)
def enable_agent_execution(settings):
    settings.agent_execution_plane_enabled = True
    settings.agent_worker_enabled = True
    settings.agent_queue_backpressure_enabled = False
    yield

@pytest.mark.asyncio
async def test_concurrent_pickup(session: AsyncSession):
    """Test that two workers do not pick up the same job."""
    queue_mgr = AgentQueueManager(session)
    
    # Enqueue a job
    job = await queue_mgr.enqueue_job(
        agent_run_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        tenant_id="test-tenant"
    )
    await session.commit()

    # Worker 1 and Worker 2 try to dequeue simultaneously
    # In a real async environment with one DB connection per request, SKIP LOCKED handles this.
    # Here we simulate by calling dequeue twice.
    job1 = await queue_mgr.dequeue_job("worker-1")
    job2 = await queue_mgr.dequeue_job("worker-2")

    assert job1 is not None
    assert job1.id == job.id
    assert job1.locked_by == "worker-1"
    
    assert job2 is None # Second worker should find no available jobs

@pytest.mark.asyncio
async def test_lease_expiration(session: AsyncSession):
    """Test that an expired lease releases the job back to the queue."""
    queue_mgr = AgentQueueManager(session)
    
    # Enqueue and lease a job
    job = await queue_mgr.enqueue_job(
        agent_run_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        tenant_id="test-tenant"
    )
    leased_job = await queue_mgr.dequeue_job("worker-1", lease_timeout_seconds=-10) # Immediately expired
    await session.commit()

    # Reclaim
    await queue_mgr.reclaim_expired_leases()
    await session.commit()

    # Verify job is back in queued status
    stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job.id)
    res = await session.execute(stmt)
    updated_job = res.scalar_one()
    assert updated_job.queue_status == "queued"
    assert updated_job.attempt_count == 1
    assert updated_job.locked_by is None

@pytest.mark.asyncio
async def test_max_attempts_to_dlq(session: AsyncSession):
    """Test that reaching max attempts sends the job to the Dead Letter Queue."""
    queue_mgr = AgentQueueManager(session)
    
    # Enqueue a job with max_attempts = 1
    job = await queue_mgr.enqueue_job(
        agent_run_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        tenant_id="test-tenant",
        max_attempts=1
    )
    
    # Lease and fail it (via expiry)
    await queue_mgr.dequeue_job("worker-1", lease_timeout_seconds=-10)
    await session.commit()
    
    await queue_mgr.reclaim_expired_leases()
    await session.commit()
    
    # Verify it's in dead_letter
    stmt = select(AgentExecutionJob).where(AgentExecutionJob.id == job.id)
    res = await session.execute(stmt)
    updated_job = res.scalar_one()
    assert updated_job.queue_status == "dead_letter"
    
    # Check DLQ table
    stmt_dlq = select(AgentExecutionDeadLetter).where(AgentExecutionDeadLetter.job_id == job.id)
    res_dlq = await session.execute(stmt_dlq)
    dlq_record = res_dlq.scalar_one_or_none()
    assert dlq_record is not None
    assert dlq_record.dlq_reason == "max_attempts_reached_after_lease_expiry"

@pytest.mark.asyncio
async def test_drain_mode(session: AsyncSession):
    """Test that a worker in drain mode does not pick up new jobs."""
    worker = AgentWorkerService(worker_id="worker-drain")
    worker.drain()
    
    # Enqueue a job
    queue_mgr = AgentQueueManager(session)
    await queue_mgr.enqueue_job(
        agent_run_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        tenant_id="test-tenant"
    )
    await session.commit()
    
    # Attempt to run once
    processed = await worker.run_once()
    assert processed is False

@pytest.mark.asyncio
async def test_idempotency_key(session: AsyncSession):
    """Test that the same idempotency key avoids duplicate job creation."""
    queue_mgr = AgentQueueManager(session)
    run_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    idem_key = "unique-key-123"
    
    job1 = await queue_mgr.enqueue_job(run_id, agent_id, "tenant-1", idempotency_key=idem_key)
    await session.commit()
    
    job2 = await queue_mgr.enqueue_job(run_id, agent_id, "tenant-1", idempotency_key=idem_key)
    await session.commit()
    
    assert job1.id == job2.id
    
    # Verify only one job exists in DB
    stmt = select(func.count(AgentExecutionJob.id)).where(AgentExecutionJob.idempotency_key == idem_key)
    res = await session.execute(stmt)
    assert res.scalar() == 1

@pytest.mark.asyncio
async def test_deduplication_key(session: AsyncSession):
    """Test that deduplication key avoids duplicate active jobs."""
    queue_mgr = AgentQueueManager(session)
    run_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    dedup_key = "dedup-key-456"
    
    job1 = await queue_mgr.enqueue_job(run_id, agent_id, "tenant-1", deduplication_key=dedup_key)
    await session.commit()
    
    # Try to enqueue another job with same dedup key while first is still active (queued)
    job2 = await queue_mgr.enqueue_job(uuid.uuid4(), agent_id, "tenant-1", deduplication_key=dedup_key)
    await session.commit()
    
    assert job1.id == job2.id
    
    # Now complete the job and try again - should allow new job
    job1.queue_status = "completed"
    await session.commit()
    
    job3 = await queue_mgr.enqueue_job(uuid.uuid4(), agent_id, "tenant-1", deduplication_key=dedup_key)
    await session.commit()
    
    assert job3.id != job1.id

