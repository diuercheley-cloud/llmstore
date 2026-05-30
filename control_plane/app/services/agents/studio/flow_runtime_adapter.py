# Owner: agent-platform
import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .flow_compiler import FlowCompiler
from .flow_validator import FlowValidator
from app.models.agent_studio import AgentFlowVersion, AgentFlowDebugSession, AgentFlowDebugEvent
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class FlowRuntimeAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compiler = FlowCompiler()
        self.validator = FlowValidator()

    async def dry_run(self, version_id: uuid.UUID, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a flow in a simulated environment without real side effects.
        """
        version = await self.db.get(AgentFlowVersion, version_id)
        if not version:
            raise ValueError("Flow version not found")

        # 1. Validate
        errors = self.validator.validate(version)
        if errors:
            return {"status": "failed", "stage": "validation", "errors": errors}

        # 2. Compile
        plan = self.compiler.compile(version)
        
        # 3. Create Debug Session
        session = AgentFlowDebugSession(
            flow_version_id=version_id,
            tenant_id="dry-run-tenant",
            status="active"
        )
        self.db.add(session)
        await self.db.flush()

        # 4. Simulate steps
        debug_events = []
        for task in plan["tasks"]:
            event = AgentFlowDebugEvent(
                session_id=session.id,
                event_type="node_execution_simulated",
                node_id=task["node_id"],
                details={
                    "task_type": task["task_type"],
                    "simulated_output": f"Success: {task['task_type']} executed without side-effects."
                }
            )
            self.db.add(event)
            debug_events.append({
                "node_id": task["node_id"],
                "status": "success",
                "message": f"Simulated {task['task_type']}"
            })

        session.status = "completed"
        await self.db.commit()

        return {
            "status": "success",
            "session_id": str(session.id),
            "trace": debug_events
        }
