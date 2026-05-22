import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentPlan, AgentTask, AgentTaskDependency, AgentTaskAttempt, AgentCompensationAction
from app.services.agents.compensation import CompensationService

logger = logging.getLogger(__name__)

class TaskEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.compensation = CompensationService(db)

    async def execute_plan(self, plan_id: uuid.UUID):
        if not self.settings.agent_plan_execution_enabled:
            raise RuntimeError("Agent plan execution is disabled.")

        res = await self.db.execute(select(AgentPlan).where(AgentPlan.id == plan_id))
        plan = res.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        plan.status = "executing"
        await self.db.commit()

        while True:
            # Find next tasks to execute (status='pending' and all dependencies 'completed')
            next_tasks = await self._get_ready_tasks(plan_id)
            if not next_tasks:
                # Check if all tasks are completed
                res_all = await self.db.execute(select(AgentTask).where(AgentTask.plan_id == plan_id))
                all_tasks = res_all.scalars().all()
                if all(t.status == "completed" or t.status == "skipped" for t in all_tasks):
                    plan.status = "completed"
                    await self.db.commit()
                    break
                elif any(t.status == "failed" for t in all_tasks):
                    plan.status = "failed"
                    await self.db.commit()
                    break
                else:
                    # Blocked or waiting approval
                    break

            for task in next_tasks:
                await self.run_task(task.id)

    async def _get_ready_tasks(self, plan_id: uuid.UUID) -> List[AgentTask]:
        # 1. Fetch pending tasks
        stmt = select(AgentTask).where(AgentTask.plan_id == plan_id, AgentTask.status == "pending")
        res = await self.db.execute(stmt)
        pending = res.scalars().all()
        
        ready = []
        for task in pending:
            # 2. Check dependencies
            res_deps = await self.db.execute(
                select(AgentTask).join(AgentTaskDependency, AgentTaskDependency.depends_on_task_id == AgentTask.id)
                .where(AgentTaskDependency.task_id == task.id)
            )
            deps = res_deps.scalars().all()
            if all(d.status == "completed" or d.status == "skipped" for d in deps):
                ready.append(task)
        
        return ready

    async def run_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if not task:
            return

        task.status = "running"
        task.attempt_count += 1
        await self.db.commit()

        attempt = AgentTaskAttempt(
            task_id=task.id,
            status="running",
            started_at=utc_now()
        )
        self.db.add(attempt)
        await self.db.commit()

        try:
            # Execution logic would go here
            # For this skeleton, we'll mark it as completed
            # In real scenario, it would call tools or model
            task.status = "completed"
            attempt.status = "completed"
            attempt.completed_at = utc_now()
        except Exception as e:
            logger.exception(f"Task {task_id} failed")
            task.status = "failed"
            attempt.status = "failed"
            attempt.error = str(e)
            attempt.completed_at = utc_now()
            
            # Compensation logic
            if task.compensation_action_id:
                await self.compensation.trigger_compensation(task.id)
            
            # Retry logic
            if self.settings.agent_auto_retry_enabled and task.attempt_count < task.max_attempts:
                task.status = "pending" # will be picked up again
        
        await self.db.commit()

    async def retry_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if task:
            task.status = "pending"
            await self.db.commit()

    async def skip_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if task:
            task.status = "skipped"
            await self.db.commit()
