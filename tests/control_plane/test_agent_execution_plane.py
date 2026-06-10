import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agent_execution import (
    AgentExecutionDeadLetter,
    AgentExecutionJob,
    AgentExecutionRetry,
)
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents import agent_runtime
from app.services.agents.agent_execution_plane import AgentExecutionPlane
from app.services.agents.agent_queue import AgentQueueManager, BackpressureError
from app.services.agents.agent_worker import AgentWorkerService
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        # Import all models to ensure they are registered on Base
        import app.models.agents.agents  # noqa
        import app.models.agents.agent_execution  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up tables after each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def run_settings():
    settings = get_settings()
    # Save original values
    orig_plane = settings.agent_execution_plane_enabled
    orig_worker = settings.agent_worker_enabled
    orig_async = settings.agent_async_execution_enabled
    orig_backpressure = settings.agent_queue_backpressure_enabled
    orig_runtime = settings.agent_runtime_enabled
    
    yield settings
    
    # Restore original values
    settings.agent_execution_plane_enabled = orig_plane
    settings.agent_worker_enabled = orig_worker
    settings.agent_async_execution_enabled = orig_async
    settings.agent_queue_backpressure_enabled = orig_backpressure
    settings.agent_runtime_enabled = orig_runtime


async def create_mock_agent(db: AsyncSession, tenant_id: str, risk_level: str = "low") -> AgentDefinition:
    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name=f"Test Agent {uuid.uuid4().hex[:4]}",
        version="1.0.0",
        description="A test agent definition",
        instructions="Return final response",
        model_id="gpt-3.5-turbo",
        owner="tester",
        tenant_id=tenant_id,
        status="active",
        risk_level=risk_level,
        max_steps=5,
        max_runtime_seconds=120,
    )
    db.add(agent_def)
    await db.commit()
    return agent_def


@pytest.mark.asyncio
async def test_disabled_flag_blocks_execution(run_settings):
    run_settings.agent_execution_plane_enabled = False
    run_settings.agent_runtime_enabled = True
    
    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        # start_run should raise RuntimeDisabledError
        with pytest.raises(agent_runtime.RuntimeDisabledError, match="Agent Execution Plane is disabled"):
            await agent_runtime.start_run(
                db=db,
                agent_id=agent.id,
                tenant_id="tenant-1",
                input_text="Hello",
            )


@pytest.mark.asyncio
async def test_async_run_creation_queues_job(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        # Start the run
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="Hello async",
        )
        
        # Verify run is enqueued and has status 'queued'
        assert run.status == "queued"
        
        # Check job in db
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        
        assert job is not None
        assert job.status == "queued"
        assert job.tenant_id == "tenant-1"
        assert job.attempts == 0


@pytest.mark.asyncio
async def test_worker_processing_e2e(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True
    run_settings.agent_worker_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="Run e2e",
        )
        
    # Start worker and run once
    worker = AgentWorkerService(worker_id="test-worker-1")
    await worker.start()
    
    # Process the job
    processed = await worker.run_once()
    assert processed is True
    
    await worker.stop()
    
    # Check job and run statuses
    async with SessionLocal() as db:
        # Refresh states
        stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res_job = await db.execute(stmt_job)
        job = res_job.scalar_one()
        
        stmt_run = select(AgentRun).where(AgentRun.id == run.id)
        res_run = await db.execute(stmt_run)
        db_run = res_run.scalar_one()
        
        assert job.status == "completed"
        assert db_run.status == "completed"


@pytest.mark.asyncio
async def test_lease_expiration_and_recovery(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="Lease test",
        )
        
        # Dequeue/Lease job manually
        queue_mgr = AgentQueueManager(db)
        job = await queue_mgr.dequeue_job("worker-dead", lease_timeout_seconds=-10)  # expires in past
        
        assert job is not None
        assert job.status == "leased"

    # Now dequeue_job should reclaim expired lease and reschedule retry
    async with SessionLocal() as db:
        queue_mgr2 = AgentQueueManager(db)
        # Reclaiming will increment attempts and re-enqueue with delay
        await queue_mgr2.reclaim_expired_leases()
        
        # Check job status
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt)
        job_updated = res.scalar_one()
        
        assert job_updated.status == "queued"
        assert job_updated.attempts == 1
        
        # Check retry log
        stmt_retry = select(AgentExecutionRetry).where(AgentExecutionRetry.job_id == job_updated.id)
        res_retry = await db.execute(stmt_retry)
        retry = res_retry.scalars().first()
        assert retry is not None
        assert "Lease expired" in retry.error_message


@pytest.mark.asyncio
async def test_retry_limits_to_dlq(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="DLQ test",
        )
        
        # Dequeue/lease job to expire it multiple times
        queue_mgr = AgentQueueManager(db)
        
        # Attempt 1: lease -> expire -> reclaim
        await queue_mgr.dequeue_job("worker-dead", lease_timeout_seconds=-10)
        await queue_mgr.reclaim_expired_leases()
        
        # Attempt 2: lease -> expire -> reclaim
        # Reset scheduled_at to make it pollable immediately
        stmt_reset = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt_reset)
        job = res.scalar_one()
        job.scheduled_at = utc_now() - timedelta(minutes=5)
        await db.commit()
        
        await queue_mgr.dequeue_job("worker-dead", lease_timeout_seconds=-10)
        await queue_mgr.reclaim_expired_leases()
        
        # Attempt 3: lease -> expire -> reclaim (Reaching max_attempts=3)
        stmt_reset2 = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res2 = await db.execute(stmt_reset2)
        job = res2.scalar_one()
        job.scheduled_at = utc_now() - timedelta(minutes=5)
        await db.commit()
        
        await queue_mgr.dequeue_job("worker-dead", lease_timeout_seconds=-10)
        await queue_mgr.reclaim_expired_leases()
        
        # Now job must be in dead_letter state
        stmt_job = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res_job = await db.execute(stmt_job)
        job_final = res_job.scalar_one()
        
        assert job_final.status == "dead_letter"
        
        # DLQ record should exist
        stmt_dlq = select(AgentExecutionDeadLetter).where(AgentExecutionDeadLetter.job_id == job_final.id)
        res_dlq = await db.execute(stmt_dlq)
        dlq = res_dlq.scalar_one_or_none()
        assert dlq is not None
        assert dlq.tenant_id == "tenant-1"


@pytest.mark.asyncio
async def test_job_cancellation(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="Cancel test",
        )
        
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt)
        job = res.scalar_one()
        
        # Cancel the job
        plane = AgentExecutionPlane(db)
        success = await plane.cancel_job(job.id, tenant_id="tenant-1")
        assert success is True
        
        # Verify job and run statuses
        await db.refresh(job)
        assert job.status == "cancelled"
        
        # Check run status
        stmt_run = select(AgentRun).where(AgentRun.id == run.id)
        res_run = await db.execute(stmt_run)
        db_run = res_run.scalar_one()
        assert db_run.status == "cancelled"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_boundary(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-A")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-A",
            input_text="Isolation test",
        )
        
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt)
        job = res.scalar_one()
        
        plane = AgentExecutionPlane(db)
        
        # Tenant B tries to cancel Tenant A's job -> should raise PermissionError
        with pytest.raises(PermissionError, match="Access denied"):
            await plane.cancel_job(job.id, tenant_id="tenant-B")
            
        # Tenant B tries to retry Tenant A's job -> should raise PermissionError
        with pytest.raises(PermissionError, match="Access denied"):
            await plane.retry_job(job.id, tenant_id="tenant-B")
            
        # Tenant A can cancel its own job
        success = await plane.cancel_job(job.id, tenant_id="tenant-A")
        assert success is True


@pytest.mark.asyncio
async def test_backpressure_thresholds(run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True
    run_settings.agent_queue_backpressure_enabled = True

    async with SessionLocal() as db:
        agent1 = await create_mock_agent(db, "tenant-1")
        agent2 = await create_mock_agent(db, "tenant-1")
        agent3 = await create_mock_agent(db, "tenant-1")
        
        # Enqueue 10 jobs to hit the tenant concurrency limit (max 10)
        # We distribute them: 4 for agent1, 4 for agent2, 2 for agent3.
        # This keeps each agent below the limit of 5, but the tenant total at 10.
        queue_mgr = AgentQueueManager(db)
        
        for i in range(4):
            await agent_runtime.start_run(
                db=db,
                agent_id=agent1.id,
                tenant_id="tenant-1",
                input_text=f"Backpressure agent1 job {i}",
            )
            
        for i in range(4):
            await agent_runtime.start_run(
                db=db,
                agent_id=agent2.id,
                tenant_id="tenant-1",
                input_text=f"Backpressure agent2 job {i}",
            )
            
        for i in range(2):
            await agent_runtime.start_run(
                db=db,
                agent_id=agent3.id,
                tenant_id="tenant-1",
                input_text=f"Backpressure agent3 job {i}",
            )
            
        # Attempt 11th run for agent3 -> should raise BackpressureError due to tenant limit
        with pytest.raises(BackpressureError, match="Tenant concurrent limit exceeded"):
            await agent_runtime.start_run(
                db=db,
                agent_id=agent3.id,
                tenant_id="tenant-1",
                input_text="Backpressure job 11",
            )


@pytest.mark.asyncio
async def test_admin_api_endpoints(async_client, admin_token_headers, run_settings):
    run_settings.agent_execution_plane_enabled = True
    run_settings.agent_runtime_enabled = True
    run_settings.agent_async_execution_enabled = True

    async with SessionLocal() as db:
        agent = await create_mock_agent(db, "tenant-1")
        
        run = await agent_runtime.start_run(
            db=db,
            agent_id=agent.id,
            tenant_id="tenant-1",
            input_text="API endpoint test",
        )
        
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run.id)
        res = await db.execute(stmt)
        job = res.scalar_one()
        
    # 1. GET /admin/agents/execution/jobs
    resp = await async_client.get("/admin/agents/execution/jobs", headers=admin_token_headers)
    assert resp.status_code == status.HTTP_200_OK
    jobs = resp.json()
    assert len(jobs) > 0
    assert any(j["id"] == str(job.id) for j in jobs)
    
    # 2. GET /admin/agents/execution/workers
    resp_workers = await async_client.get("/admin/agents/execution/workers", headers=admin_token_headers)
    assert resp_workers.status_code == status.HTTP_200_OK
    
    # 3. POST /admin/agents/execution/jobs/{id}/cancel
    resp_cancel = await async_client.post(
        f"/admin/agents/execution/jobs/{job.id}/cancel",
        headers=admin_token_headers
    )
    assert resp_cancel.status_code == status.HTTP_200_OK
    assert resp_cancel.json()["status"] == "cancelled"
    
    # 4. POST /admin/agents/execution/jobs/{id}/retry
    resp_retry = await async_client.post(
        f"/admin/agents/execution/jobs/{job.id}/retry",
        headers={**admin_token_headers, "X-Tenant-ID": "tenant-1"}
    )
    assert resp_retry.status_code == status.HTTP_200_OK
    assert resp_retry.json()["status"] == "retrying"
