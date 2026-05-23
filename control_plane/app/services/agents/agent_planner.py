# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.models.agents import AgentPlan, AgentTask, AgentTaskDependency
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class AgentPlanner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def create_plan(self, run_id: uuid.UUID, goal: str, tasks_data: List[dict]) -> AgentPlan:
        if not self.settings.agent_planning_enabled:
            logger.warning("Agent planning is disabled.")

        # Calculate initial risk score based on task types and tools
        risk_score = 0.0
        requires_approval = False
        for t in tasks_data:
            if t.get("task_type") in ("destructive", "external"):
                risk_score += 0.5
                requires_approval = True
            elif t.get("task_type") == "tool_call":
                risk_score += 0.1

        plan = AgentPlan(
            agent_run_id=run_id,
            goal_hash=agent_state.compute_sha256(goal),
            status="draft",
            risk_score=min(risk_score, 1.0),
            requires_approval=requires_approval
        )
        self.db.add(plan)
        await self.db.flush()

        task_map = {} # temp map to handle dependencies by index or title
        
        created_tasks = []
        for i, t_data in enumerate(tasks_data):
            task = AgentTask(
                plan_id=plan.id,
                title=t_data["title"],
                description_hash=agent_state.compute_sha256(t_data.get("description", "")),
                task_type=t_data.get("task_type", "tool_call"),
                max_attempts=t_data.get("max_attempts", 3),
                input_data=t_data.get("input_data", {})
            )
            self.db.add(task)
            created_tasks.append((task, t_data))
            task_map[t_data.get("ref", i)] = task
            task_map[t_data["title"]] = task

        await self.db.flush()

        # Handle dependencies
        for task, t_data in created_tasks:
            deps = t_data.get("dependencies", [])
            for d_ref in deps:
                if d_ref in task_map:
                    dep = AgentTaskDependency(
                        task_id=task.id,
                        depends_on_task_id=task_map[d_ref].id
                    )
                    self.db.add(dep)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_plan(self, plan_id: uuid.UUID) -> Optional[AgentPlan]:
        res = await self.db.execute(select(AgentPlan).where(AgentPlan.id == plan_id))
        return res.scalar_one_or_none()

    async def update_plan_status(self, plan_id: uuid.UUID, status: str):
        plan = await self.get_plan(plan_id)
        if plan:
            plan.status = status
            await self.db.commit()
