import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agents import AgentRun, AgentRunStep
from app.core.time import utc_now

logger = logging.getLogger(__name__)


class StudioDebugger:
    """
    Builds time-travel debugger views for Studio flow runs.
    Provides reasoning traces, step-by-step execution views,
    and sanitized chain-of-thought inspection.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def build_view(self, run_id: str) -> Dict[str, Any]:
        if not self.db:
            return {
                "run_id": run_id,
                "reasoning_summary": "No database session available",
                "raw_chain_of_thought_exposed": False,
            }

        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            return {"run_id": run_id, "error": "Invalid run_id format"}

        run = await self.db.get(AgentRun, run_uuid)
        if not run:
            return {"run_id": run_id, "error": "Run not found"}

        stmt = select(AgentRunStep).where(
            AgentRunStep.run_id == run_uuid
        ).order_by(AgentRunStep.step_number)
        res = await self.db.execute(stmt)
        steps = list(res.scalars().all())

        step_summaries = []
        for s in steps:
            summary = {
                "step_number": s.step_number,
                "step_type": s.step_type,
                "timestamp": s.created_at.isoformat() if s.created_at else None,
            }
            if s.step_type in ("llm_call", "reasoning", "thought"):
                summary["content_preview"] = (
                    s.output[:200] + "..." if s.output and len(s.output) > 200 else s.output
                ) if s.output else None
            if s.step_type in ("tool_call", "tool_result"):
                meta = s.step_metadata or {}
                summary["tool_name"] = meta.get("tool_name", meta.get("tool", "unknown"))
            step_summaries.append(summary)

        return {
            "run_id": run_id,
            "agent_id": str(run.agent_id) if run.agent_id else None,
            "status": run.status,
            "total_steps": len(steps),
            "total_tokens": run.total_tokens,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "step_execution": step_summaries,
            "reasoning_summary": self._summarize_reasoning(steps),
            "raw_chain_of_thought_exposed": False,
        }

    def _summarize_reasoning(self, steps: List[AgentRunStep]) -> str:
        if not steps:
            return "No reasoning steps recorded"

        llm_calls = [s for s in steps if s.step_type in ("llm_call", "reasoning")]
        tool_calls = [s for s in steps if s.step_type == "tool_call"]
        approvals = [s for s in steps if s.step_type == "approval"]

        parts = []
        if llm_calls:
            parts.append(f"{len(llm_calls)} LLM reasoning steps")
        if tool_calls:
            tools_used = set()
            for tc in tool_calls:
                meta = tc.step_metadata or {}
                tool_name = meta.get("tool_name", meta.get("tool", "unknown"))
                tools_used.add(tool_name)
            parts.append(f"{len(tool_calls)} tool calls ({', '.join(sorted(tools_used))})")
        if approvals:
            parts.append(f"{len(approvals)} approval requests")

        return "; ".join(parts) if parts else "Standard execution flow"
