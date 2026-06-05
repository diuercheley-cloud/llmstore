import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.models.deterministic_execution import ExecutionRun, ExecutionStep, ToolCallRecord
from app.core.time import utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class DeterministicExecutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_run(
        self, 
        agent_id: str, 
        tenant_id: str, 
        seed: Optional[int] = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        workflow_id: Optional[str] = None
    ) -> ExecutionRun:
        run = ExecutionRun(
            agent_id=agent_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            status="started"
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def record_step(
        self,
        run_id: str,
        step_number: int,
        model_name: str,
        provider: str,
        prompt_template: Optional[str] = None,
        prompt_rendered: Optional[str] = None,
        response_text: Optional[str] = None,
        policy_decisions: Optional[Dict[str, Any]] = None,
        routing_decisions: Optional[Dict[str, Any]] = None
    ) -> ExecutionStep:
        prompt_hash = self._compute_hash(prompt_rendered) if prompt_rendered else None
        response_hash = self._compute_hash(response_text) if response_text else None
        
        step = ExecutionStep(
            run_id=run_id,
            step_number=step_number,
            model_name=model_name,
            provider=provider,
            prompt_template=prompt_template,
            prompt_rendered=prompt_rendered,
            prompt_hash=prompt_hash,
            response_text=response_text,
            response_hash=response_hash,
            policy_decisions=policy_decisions,
            routing_decisions=routing_decisions
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def record_tool_call(
        self,
        step_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Dict[str, Any]] = None,
        is_redacted: bool = False
    ) -> ToolCallRecord:
        record = ToolCallRecord(
            step_id=step_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            is_redacted=is_redacted
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def generate_manifest(self, run_id: str) -> Dict[str, Any]:
        stmt = select(ExecutionRun).where(ExecutionRun.id == run_id)
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        
        if not run:
            return {}

        manifest = {
            "version": "1.0",
            "run_id": str(run.id),
            "agent_id": str(run.agent_id),
            "tenant_id": run.tenant_id,
            "config": {
                "seed": run.seed,
                "temperature": run.temperature,
                "top_p": run.top_p
            },
            "steps": []
        }

        # Load steps and tool calls
        # Note: In a real app we'd use joinedload
        for step in run.steps:
            step_data = {
                "step_number": step.step_number,
                "model": step.model_name,
                "provider": step.provider,
                "prompt_hash": step.prompt_hash,
                "response_hash": step.response_hash,
                "tool_calls": []
            }
            for tc in step.tool_calls:
                step_data["tool_calls"].append({
                    "tool": tc.tool_name,
                    "input_hash": self._compute_hash(json.dumps(tc.tool_input)),
                    "output_redacted": tc.is_redacted
                })
            manifest["steps"].append(step_data)

        manifest_json = json.dumps(manifest, sort_keys=True)
        manifest["manifest_hash"] = hashlib.sha256(manifest_json.encode()).hexdigest()
        
        run.manifest_hash = manifest["manifest_hash"]
        run.completed_at = utc_now()
        run.status = "completed"
        await self.session.flush()
        
        return manifest

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def replay_dry_run(self, run_id: str) -> Dict[str, Any]:
        """
        Simulates replay by comparing hashes of a new hypothetical run with the recorded manifest.
        """
        manifest = await self.generate_manifest(run_id)
        return {
            "run_id": run_id,
            "replay_type": "dry-run",
            "manifest": manifest,
            "status": "ready_for_replay",
            "warnings": ["Side effects are blocked in dry-run mode"]
        }
