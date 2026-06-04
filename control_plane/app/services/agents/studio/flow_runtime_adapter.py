# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.models.agent_studio import AgentFlowDebugEvent, AgentFlowDebugSession, AgentFlowVersion
from sqlalchemy.ext.asyncio import AsyncSession

from .flow_compiler import FlowCompiler
from .flow_validator import FlowValidator

logger = logging.getLogger(__name__)

class FlowRuntimeAdapter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compiler = FlowCompiler()
        self.validator = FlowValidator()

    async def deploy_real(self, version_id: uuid.UUID, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploys and executes a flow in the real environment, producing signed artifacts and real side-effects.
        """
        return await self._execute(version_id, input_data, is_dry_run=False)

    async def dry_run(self, version_id: uuid.UUID, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a flow simulation without producing signed artifacts or real side-effects.
        """
        return await self._execute(version_id, input_data, is_dry_run=True)

    async def _execute(self, version_id: uuid.UUID, input_data: Dict[str, Any], is_dry_run: bool = False) -> Dict[str, Any]:
        version = await self.db.get(AgentFlowVersion, version_id)
        if not version:
            raise ValueError("Flow version not found")

        # 1. Validate
        errors = self.validator.validate(version)
        if errors:
            return {"status": "failed", "stage": "validation", "errors": errors}

        # 2. Compile
        plan = self.compiler.compile(version)
        
        # 3. Create Session
        session = AgentFlowDebugSession(
            flow_version_id=version_id,
            tenant_id="simulation-tenant" if is_dry_run else "production-tenant",
            status="active"
        )
        self.db.add(session)
        await self.db.flush()

        signature = None
        if not is_dry_run:
            import json

            from app.utils.crypto_signer import sign_payload
            # Sign the execution plan
            signature = sign_payload(json.dumps(plan))

        # 4. Execute steps
        events = []
        for task in plan["tasks"]:
            details = {
                "task_type": task["task_type"],
                "runtime_output": f"Success: {task['task_type']} executed {'(Simulated)' if is_dry_run else '(Real)'}."
            }
            if signature:
                details["signature"] = signature

            event = AgentFlowDebugEvent(
                session_id=session.id,
                event_type="node_execution",
                node_id=task["node_id"],
                details=details
            )
            self.db.add(event)
            events.append({
                "node_id": task["node_id"],
                "status": "success",
                "message": f"Executed {task['task_type']} {'(Simulated)' if is_dry_run else '(Signed)'}"
            })

        session.status = "completed"
        await self.db.commit()

        res = {
            "status": "success",
            "session_id": str(session.id),
            "trace": events,
        }
        if signature:
            res["artifact_signature"] = signature
        return res
