# Owner: agent-platform
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_workflows import AgentWorkflowRun, AgentWorkflow
from app.services.agents.workflows.workflow_state_machine import WorkflowStateMachine, WorkflowStatus
from app.services.agents.workflows.workflow_locks import WorkflowLockManager

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Main orchestration engine for stateful workflows.
    Handles run lifecycle, persistence, and execution of workflow steps.
    """
    
    def __init__(self, db: AsyncSession, worker_id: str = "default_worker"):
        self.db = db
        self.worker_id = worker_id
        self.settings = get_settings()
        self.locks = WorkflowLockManager(db)

    async def create_run(self, workflow_id: uuid.UUID, tenant_id: str, input_data: Dict[str, Any]) -> AgentWorkflowRun:
        run = AgentWorkflowRun(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=WorkflowStatus.CREATED.value,
            current_state="start",
            state_data={},
            context=input_data,
            next_execution_at=utc_now()
        )
        self.db.add(run)
        await self.db.commit()
        return run

    async def process_ready_runs(self):
        """
        Finds and processes workflow runs that are ready for execution.
        """
        if not self.settings.agent_stateful_workflows_enabled:
            return

        stmt = select(AgentWorkflowRun).where(
            AgentWorkflowRun.status.in_([
                WorkflowStatus.CREATED.value,
                WorkflowStatus.RUNNING.value,
                WorkflowStatus.RETRY_SCHEDULED.value
            ]),
            AgentWorkflowRun.next_execution_at <= utc_now()
        ).limit(10)
        
        res = await self.db.execute(stmt)
        runs = res.scalars().all()
        
        for run in runs:
            await self.execute_step(run.id)

    async def execute_step(self, run_id: uuid.UUID):
        """
        Executes a single step of a workflow run with distributed locking.
        """
        lock_key = f"workflow_run:{run_id}"
        owner_id = uuid.uuid5(uuid.NAMESPACE_DNS, self.worker_id)
        if not await self.locks.acquire_lock(lock_key, owner_id):
            return

        try:
            stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
            res = await self.db.execute(stmt)
            run = res.scalar_one_or_none()
            if not run:
                return

            sm = WorkflowStateMachine(run)
            await sm.transition_to(WorkflowStatus.RUNNING)
            await self.db.commit()

            # Execute logic (this would normally call a user-defined workflow class)
            # For this prototype, we simulate a step based on context
            await self._simulate_workflow_logic(run, sm)
            
            await self.db.commit()
        except Exception as e:
            logger.exception(f"Error executing workflow {run_id}")
            # Handle failure, retries, etc.
            await self._handle_failure(run_id, e)
        finally:
            await self.locks.release_lock(lock_key, owner_id)

    async def _simulate_workflow_logic(self, run: AgentWorkflowRun, sm: WorkflowStateMachine):
        """
        Placeholder for actual workflow execution logic.
        In a real implementation, this would lookup the workflow implementation 
        and call its current state handler.
        """
        context = sm.get_context()
        current_state = run.current_state

        # Mock: if it's 'start', move to 'process'
        if current_state == "start":
            sm.update_context({"step": 1})
            sm.set_current_state("process")
            await sm.transition_to(WorkflowStatus.RUNNING)
        elif current_state == "process":
            # Simulate a long-running wait or approval
            if context.get("requires_approval"):
                await sm.transition_to(WorkflowStatus.WAITING_APPROVAL)
            elif context.get("sleep_seconds"):
                from datetime import timedelta
                run.next_execution_at = utc_now() + timedelta(seconds=context["sleep_seconds"])
                await sm.transition_to(WorkflowStatus.SLEEPING)
            else:
                sm.set_current_state("end")
                await sm.transition_to(WorkflowStatus.COMPLETED)
        
    async def _handle_failure(self, run_id: uuid.UUID, error: Exception):
        stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            run.retry_count += 1
            if run.retry_count >= run.max_retries:
                run.status = WorkflowStatus.FAILED.value
                # Move to DLQ logic could be here
            else:
                from datetime import timedelta
                run.status = WorkflowStatus.RETRY_SCHEDULED.value
                run.next_execution_at = utc_now() + timedelta(minutes=2**run.retry_count)
            await self.db.commit()

    async def signal_run(self, run_id: uuid.UUID, signal_name: str, payload: Dict[str, Any]):
        from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
        signals = WorkflowSignalManager(self.db)
        await signals.send_signal(run_id, signal_name, payload)

    async def cancel_run(self, run_id: uuid.UUID):
        stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            sm = WorkflowStateMachine(run)
            await sm.transition_to(WorkflowStatus.CANCELLED)
            await self.db.commit()
