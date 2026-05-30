# Owner: agent-platform
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent_workflows import AgentWorkflowRun, AgentSubworkflowRun, AgentWorkflowDefinition
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class SubworkflowRuntime:
    """
    Manages the lifecycle of sub-workflows within a parent workflow.
    Handles versioning, inputs/outputs, and state tracking.
    """
    
    def __init__(self, db: AsyncSession, parent_run: AgentWorkflowRun):
        self.db = db
        self.parent_run = parent_run

    async def start_subworkflow(self, node_key: str, definition_id: uuid.UUID, input_data: Dict[str, Any]) -> AgentSubworkflowRun:
        """
        Initializes a sub-workflow run record.
        Actual execution will be triggered by the main engine.
        """
        # Verify definition exists and potentially validate schema
        stmt = select(AgentWorkflowDefinition).where(AgentWorkflowDefinition.id == definition_id)
        result = await self.db.execute(stmt)
        definition = result.scalar_one_or_none()
        if not definition:
            raise ValueError(f"Subworkflow definition {definition_id} not found.")

        sub_run = AgentSubworkflowRun(
            parent_run_id=self.parent_run.id,
            subworkflow_definition_id=definition_id,
            node_key=node_key,
            status="pending",
            input_data=input_data
        )
        self.db.add(sub_run)
        await self.db.flush()
        return sub_run

    async def update_subworkflow_status(self, sub_run_id: uuid.UUID, status: str, output_data: Optional[Dict[str, Any]] = None):
        stmt = select(AgentSubworkflowRun).where(AgentSubworkflowRun.id == sub_run_id)
        result = await self.db.execute(stmt)
        sub_run = result.scalar_one_or_none()
        
        if sub_run:
            sub_run.status = status
            if output_data is not None:
                sub_run.output_data = output_data
            sub_run.updated_at = utc_now()
            await self.db.flush()

    async def get_subworkflow_results(self, node_key: str) -> Optional[Dict[str, Any]]:
        stmt = select(AgentSubworkflowRun).where(
            AgentSubworkflowRun.parent_run_id == self.parent_run.id,
            AgentSubworkflowRun.node_key == node_key
        ).order_by(AgentSubworkflowRun.created_at.desc())
        
        result = await self.db.execute(stmt)
        sub_run = result.scalar_one_or_none()
        
        if sub_run and sub_run.status == "completed":
            return sub_run.output_data
        return None

    async def is_subworkflow_complete(self, node_key: str) -> bool:
        stmt = select(AgentSubworkflowRun.status).where(
            AgentSubworkflowRun.parent_run_id == self.parent_run.id,
            AgentSubworkflowRun.node_key == node_key
        ).order_by(AgentSubworkflowRun.created_at.desc())
        
        result = await self.db.execute(stmt)
        status = result.scalar_one_or_none()
        return status == "completed"
