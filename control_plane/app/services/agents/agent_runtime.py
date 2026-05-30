# Owner: agent-platform
import uuid
import logging
import asyncio
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.time import utc_now
from app.services.agents import agent_state
from app.services.agents.agent_executor import AgentExecutor

logger = logging.getLogger(__name__)

_TEST_MOCKS = {}

class RuntimeDisabledError(RuntimeError):
    """Raised when the agent runtime is disabled."""
    pass

class ReplayDisabledError(RuntimeError):
    """Raised when the agent replay is disabled."""
    pass

def _verify_runtime_enabled():
    settings = get_settings()
    if not settings.agent_execution_plane_enabled:
        raise RuntimeDisabledError("Agent Execution Plane is disabled. Set AGENT_EXECUTION_PLANE_ENABLED=true to enable it.")
    if not settings.agent_runtime_enabled:
        raise RuntimeDisabledError("Agent runtime is disabled. Set AGENT_RUNTIME_ENABLED=true to enable it.")

async def start_run(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tenant_id: str,
    input_text: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    llm_provider: Optional[Any] = None,
    tool_runner: Optional[Any] = None,
) -> Any:
    """Initializes and starts an agent execution run."""
    _verify_runtime_enabled()
    
    # 1. Verify agent definition exists and is active/draft
    agent_def = await agent_state.get_agent_definition(db, agent_id)
    if not agent_def:
        raise ValueError(f"Agent definition not found: {agent_id}")
        
    if agent_def.status == "deprecated":
        raise ValueError("Cannot execute a deprecated agent definition.")

    # 2. Create the run
    run = await agent_state.create_agent_run(
        db=db,
        agent_id=agent_id,
        tenant_id=tenant_id,
        input_text=input_text,
        user_id=user_id,
        correlation_id=correlation_id,
    )
    
    if llm_provider or tool_runner:
        _TEST_MOCKS[run.id] = {
            "llm_provider": llm_provider,
            "tool_runner": tool_runner,
        }
    
    # Log start event
    await agent_state.log_run_event(db, run.id, "run_started", {"started_at": str(run.started_at)})

    # 3. Trigger execution loop
    settings = get_settings()
    if settings.agent_async_execution_enabled:
        # Enqueue job in execution plane
        logger.info(f"Enqueuing run {run.id} in agent queue")
        from app.services.agents.agent_queue import AgentQueueManager
        queue_mgr = AgentQueueManager(db)
        await queue_mgr.enqueue_job(
            agent_run_id=run.id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            max_attempts=3,
        )
    else:
        # Sync execution
        logger.info(f"Running synchronous execution for run {run.id}")
        await run_execution_loop(db, run.id, llm_provider, tool_runner)
        # Refresh run state to get updated fields after sync execution
        await db.refresh(run)

    return run

async def run_execution_loop(
    db: AsyncSession,
    run_id: uuid.UUID,
    llm_provider: Optional[Any] = None,
    tool_runner: Optional[Any] = None,
):
    """Loops through executor steps until execution terminates."""
    if not llm_provider or not tool_runner:
        mocks = _TEST_MOCKS.get(run_id, {})
        if not llm_provider:
            llm_provider = mocks.get("llm_provider")
        if not tool_runner:
            tool_runner = mocks.get("tool_runner")

    try:
        executor = AgentExecutor(db, run_id, llm_provider, tool_runner)
        # Update run status to running
        await agent_state.update_run(db, run_id, status="running")
        
        while True:
            # Check if run state was modified externally (paused/cancelled)
            run = await agent_state.get_agent_run(db, run_id)
            if not run or run.status in ("paused", "cancelled", "completed", "failed", "waiting_approval"):
                break
                
            should_continue = await executor.execute_step()
            if not should_continue:
                break
                
            # Yield control briefly
            await asyncio.sleep(0.01)
            
    except Exception as e:
        logger.exception(f"Execution loop failed for run {run_id}")
        await agent_state.update_run(
            db, run_id, status="failed", failure_reason=str(e), completed_at=utc_now()
        )
        await agent_state.log_run_event(db, run_id, "run_failed", {"error": str(e)})

async def pause_run(db: AsyncSession, run_id: uuid.UUID) -> Optional[Any]:
    _verify_runtime_enabled()
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")
    if run.status not in ("running", "queued"):
        raise ValueError(f"Cannot pause a run in status: {run.status}")
        
    updated = await agent_state.update_run(db, run_id, status="paused")
    await agent_state.log_run_event(db, run_id, "run_paused", {"paused_at": str(utc_now())})
    return updated

async def resume_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    llm_provider: Optional[Any] = None,
    tool_runner: Optional[Any] = None,
) -> Optional[Any]:
    _verify_runtime_enabled()
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")
    if run.status not in ("paused", "waiting_approval"):
        raise ValueError(f"Cannot resume a run that is not paused or waiting approval. Status: {run.status}")

    if run.status == "waiting_approval":
        from sqlalchemy import select
        from app.models.agents import AgentApprovalRequest
        stmt = select(AgentApprovalRequest).where(
            AgentApprovalRequest.agent_run_id == run_id,
            AgentApprovalRequest.status == "approved"
        )
        res = await db.execute(stmt)
        if not res.scalars().first():
            raise ValueError("Cannot resume a waiting_approval run without an approved request.")

    return await resume_run_internal(db, run_id, llm_provider, tool_runner)

async def resume_run_internal(
    db: AsyncSession,
    run_id: uuid.UUID,
    llm_provider: Optional[Any] = None,
    tool_runner: Optional[Any] = None,
) -> Optional[Any]:
    _verify_runtime_enabled()
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")

    settings = get_settings()
    if settings.agent_async_execution_enabled:
        from app.models.agent_execution import AgentExecutionJob
        from sqlalchemy import select
        stmt = select(AgentExecutionJob).where(AgentExecutionJob.agent_run_id == run_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            job.queue_status = "queued"
            job.available_at = utc_now()
            job.updated_at = utc_now()
        else:
            from app.services.agents.agent_queue import AgentQueueManager
            queue_mgr = AgentQueueManager(db)
            await queue_mgr.enqueue_job(
                agent_run_id=run_id,
                agent_id=run.agent_id,
                tenant_id=run.tenant_id,
                max_attempts=3
            )
        updated = await agent_state.update_run(db, run_id, status="queued")
        await db.commit()
    else:
        updated = await agent_state.update_run(db, run_id, status="running")
        await agent_state.log_run_event(db, run_id, "run_resumed", {"resumed_at": str(utc_now())})
        await run_execution_loop(db, run_id, llm_provider, tool_runner)
        await db.refresh(updated)

    return updated

async def cancel_run(db: AsyncSession, run_id: uuid.UUID) -> Optional[Any]:
    _verify_runtime_enabled()
    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")
    if run.status in ("completed", "failed", "cancelled"):
        raise ValueError(f"Cannot cancel a run that has already finished. Status: {run.status}")

    from app.services.agents.agent_cancellation import AgentCancellationService
    await AgentCancellationService.cancel_run(db, run_id)
    await db.refresh(run)
    return run

async def replay_run(db: AsyncSession, run_id: uuid.UUID) -> Dict[str, Any]:
    """
    Simulates / replays a run in a read-only fashion using existing checkpoints and steps.
    Crucially: does not run any side effects (like actual LLM provider or tools).
    """
    settings = get_settings()
    if not settings.agent_replay_enabled:
        raise ReplayDisabledError("Replay features are disabled. Set AGENT_REPLAY_ENABLED=true to enable them.")

    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        raise ValueError(f"Agent run not found: {run_id}")

    steps = await agent_state.get_run_steps(db, run_id)
    checkpoints = await agent_state.get_run_checkpoints(db, run_id)

    # Replay runs through steps and verifies them, logging metadata without calling external components
    logger.info(f"Replaying run {run_id} read-only. Verification of {len(steps)} steps.")

    executor = AgentExecutor(db, run_id, is_replay=True)
    # The user might want to actually re-run the logic but with is_replay=True
    # For now, we return the data as requested, but the executor is ready for more complex replays.

    return {
        "run_id": run_id,
        "agent_id": run.agent_id,
        "status": run.status,
        "input_hash": run.input_hash,
        "output_hash": run.output_hash,
        "total_steps": run.total_steps,
        "steps": [
            {
                "step_number": s.step_number,
                "step_type": s.step_type,
                "input_hash": s.input_hash,
                "output_hash": s.output_hash,
                "status": s.status,
                "latency_ms": s.latency_ms,
                "error": s.error,
            }
            for s in steps
        ],
        "checkpoints": [
            {
                "step_number": cp.step_number,
                "checkpoint_time": cp.checkpoint_time.isoformat() if cp.checkpoint_time else None,
                "state_snapshot": cp.state_snapshot,
            }
            for cp in checkpoints
        ]
    }
