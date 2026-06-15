# Owner: agent-platform
import logging
import uuid
from datetime import timedelta

from app.core.time import utc_now
from app.models.agents.agent_workflows import (
    AgentWorkflowNode,
    AgentWorkflowParallelGroup,
    AgentWorkflowRun,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WorkflowParallelManager:
    """
    Handles fan-out and fan-in parallelism for workflows.
    Manages parallel groups, branch tracking, and join conditions.
    """

    def __init__(self, db: AsyncSession, run: AgentWorkflowRun):
        self.db = db
        self.run = run

    async def create_parallel_group(
        self, node: AgentWorkflowNode, branches_count: int
    ) -> AgentWorkflowParallelGroup:
        config = node.config
        group = AgentWorkflowParallelGroup(
            run_id=self.run.id,
            fanout_node_key=node.node_key,
            parallelism_limit=config.get("parallelism_limit", 0),
            timeout_seconds=config.get("timeout_seconds"),
            failure_policy=config.get("failure_policy", "fail_fast"),
            branches_count=branches_count,
            status="active",
        )
        self.db.add(group)
        await self.db.flush()
        return group

    async def get_active_group(self, fanout_node_key: str) -> AgentWorkflowParallelGroup | None:
        stmt = select(AgentWorkflowParallelGroup).where(
            AgentWorkflowParallelGroup.run_id == self.run.id,
            AgentWorkflowParallelGroup.fanout_node_key == fanout_node_key,
            AgentWorkflowParallelGroup.status == "active",
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def record_branch_completion(self, group_id: uuid.UUID, success: bool = True):
        stmt = select(AgentWorkflowParallelGroup).where(AgentWorkflowParallelGroup.id == group_id)
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return

        if success:
            group.completed_branches_count += 1
        else:
            group.failed_branches_count += 1
            if group.failure_policy == "fail_fast":
                group.status = "failed"
                return

        if group.completed_branches_count + group.failed_branches_count >= group.branches_count:
            group.status = "completed"

    async def is_group_complete(self, fanout_node_key: str) -> bool:
        group = await self.get_active_group(fanout_node_key)
        if not group:
            # Check if it was already completed
            stmt = select(AgentWorkflowParallelGroup).where(
                AgentWorkflowParallelGroup.run_id == self.run.id,
                AgentWorkflowParallelGroup.fanout_node_key == fanout_node_key,
                AgentWorkflowParallelGroup.status == "completed",
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        return group.status == "completed"

    async def check_timeouts(self):
        """Checks for timed out parallel groups."""
        stmt = select(AgentWorkflowParallelGroup).where(
            AgentWorkflowParallelGroup.run_id == self.run.id,
            AgentWorkflowParallelGroup.status == "active",
            AgentWorkflowParallelGroup.timeout_seconds.is_not(None),
        )
        result = await self.db.execute(stmt)
        active_groups = result.scalars().all()

        now = utc_now()
        for group in active_groups:
            if now > group.created_at + timedelta(seconds=group.timeout_seconds):
                logger.warning(f"Parallel group {group.id} timed out.")
                group.status = "failed"
                # Here we might trigger compensation or failure in the main engine
