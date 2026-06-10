import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.agent_studio import AgentFlowDefinition, AgentFlowVersion
from app.models.agents.agent_workflows import AgentWorkflowRun
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.workflows.workflow_dag import WorkflowDAG
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class StudioWorkflowBridge:
    """
    Bridges Studio visual flows with the WorkflowEngine.
    Takes a compiled flow version and executes it as a workflow run.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.compiler = FlowCompiler()
        self.validator = FlowValidator()

    async def deploy_flow_as_workflow(
        self,
        flow_id: uuid.UUID,
        tenant_id: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> AgentWorkflowRun:
        flow = await self.db.get(AgentFlowDefinition, flow_id)
        if not flow or flow.tenant_id != tenant_id:
            raise ValueError("Flow not found or access denied")

        # Get active version
        from app.models.agents.agent_studio import AgentFlowVersion
        from sqlalchemy import select
        stmt = select(AgentFlowVersion).where(
            AgentFlowVersion.flow_id == flow_id,
            AgentFlowVersion.is_active == True,
        )
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            raise ValueError("Flow has no active version")

        # Validate
        errors = self.validator.validate(version)
        if errors:
            raise ValueError(f"Flow validation failed: {errors}")

        # Compile
        plan = self.compiler.compile(version)

        # Create workflow definition from flow
        from app.models.agents.agent_workflows import AgentWorkflowDefinition
        wf_def = AgentWorkflowDefinition(
            name=flow.name,
            tenant_id=tenant_id,
            description=flow.description,
            dag_config={"tasks": plan["tasks"]},
        )
        self.db.add(wf_def)
        await self.db.flush()

        # Run via WorkflowEngine
        engine = WorkflowEngine(self.db)
        run = await engine.create_run(
            workflow_definition_id=wf_def.id,
            tenant_id=tenant_id,
            input_data=input_data or {},
        )
        return run

    async def compile_flow_to_dag(
        self,
        version_id: uuid.UUID,
    ) -> Dict[str, Any]:
        version = await self.db.get(AgentFlowVersion, version_id)
        if not version:
            raise ValueError("Version not found")

        plan = self.compiler.compile(version)

        dag = WorkflowDAG()
        dag.build_from_tasks(plan["tasks"])
        return {
            "flow_id": str(version.flow_id),
            "version_id": str(version.id),
            "tasks": plan["tasks"],
            "topological_order": dag.topological_sort(),
            "critical_path": dag.critical_path(),
        }
