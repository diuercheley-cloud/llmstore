# Owner: agent-platform
import logging
import uuid

from app.models.agents.agents import AgentPlan, AgentPlanCostEstimate, AgentTask, AgentTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class CostAwarePlanner:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def estimate_plan_cost(self, plan_id: uuid.UUID) -> AgentPlanCostEstimate:
        """
        Estimates the cost of a plan based on its tasks, expected tokens, and tool usage.
        """
        stmt = select(AgentPlan).where(AgentPlan.id == plan_id)
        res = await self.db.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        stmt = select(AgentTask).where(AgentTask.plan_id == plan_id)
        res = await self.db.execute(stmt)
        tasks = res.scalars().all()

        total_tokens = 0
        total_tool_cost = 0.0
        total_runtime = 0.0
        total_approval_cost = 0.0

        for task in tasks:
            # Token estimation (context grows with steps)
            total_tokens += 1000 + (len(tasks) * 100)

            if task.task_type == "tool_call":
                # Try to get real tool cost
                tool_stmt = select(AgentTool).where(AgentTool.name == task.title)
                tool_res = await self.db.execute(tool_stmt)
                tool = tool_res.scalar_one_or_none()

                if tool:
                    total_tool_cost += tool.max_cost_brl or 0.10
                    total_runtime += tool.timeout_seconds or 30.0
                    if tool.requires_approval:
                        total_approval_cost += 0.50  # Operational cost of approval
                else:
                    total_tool_cost += 0.20
                    total_runtime += 10.0

            elif task.task_type == "model_call":
                total_tokens += 2000
                total_runtime += 5.0

        # Base overhead
        total_runtime += 2.0

        total_estimated_cost = total_tool_cost + (total_tokens / 1000 * 0.02) + total_approval_cost

        estimate = AgentPlanCostEstimate(
            plan_id=plan_id,
            estimated_tokens=total_tokens,
            estimated_tool_cost_brl=total_tool_cost,
            estimated_runtime_seconds=total_runtime,
            estimated_approval_cost_brl=total_approval_cost,
            total_estimated_cost_brl=total_estimated_cost,
        )
        self.db.add(estimate)
        await self.db.flush()

        logger.info(f"Generated cost estimate for plan {plan_id}: {total_estimated_cost} BRL")
        return estimate

    async def choose_optimal_plan(self, plan_candidates: list[AgentPlan]) -> AgentPlan:
        """
        Chooses the most cost-effective plan among candidates with equivalent quality.
        """
        if not plan_candidates:
            raise ValueError("No plan candidates provided")

        if len(plan_candidates) == 1:
            return plan_candidates[0]

        best_plan = None
        min_cost = float("inf")

        for plan in plan_candidates:
            estimate = await self.estimate_plan_cost(plan.id)
            if estimate.total_estimated_cost_brl < min_cost:
                min_cost = estimate.total_estimated_cost_brl
                best_plan = plan

        logger.info(f"Selected optimal plan {best_plan.id} with estimated cost {min_cost} BRL")
        return best_plan
