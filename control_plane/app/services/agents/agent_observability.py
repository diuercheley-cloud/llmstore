import uuid
import logging
import hashlib
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import metrics
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentTraceSpan, AgentTimelineEvent

logger = logging.getLogger(__name__)

class AgentObservabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def record_run_start(self, agent_id: uuid.UUID, run_id: uuid.UUID, tenant_id: str):
        if not self.settings.agent_observability_enabled:
            return
        
        # Hash tenant_id for privacy in logs/exports if enabled
        hashed_tenant = self._hash_tenant(tenant_id)
        
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status="started").inc()
        await self._record_timeline_event(run_id, "run.started", {"tenant_hash": hashed_tenant})

    async def record_step(self, agent_id: uuid.UUID, run_id: uuid.UUID, step_type: str, duration_ms: float):
        metrics.LLM_AGENT_STEP_LATENCY_SECONDS.labels(agent_id=str(agent_id), step_type=step_type).observe(duration_ms / 1000.0)
        await self._record_timeline_event(run_id, f"step.{step_type}", {"duration_ms": duration_ms})

    async def record_tool_call(self, agent_id: uuid.UUID, run_id: uuid.UUID, tool_name: str, duration_ms: float, success: bool):
        metrics.LLM_AGENT_TOOL_DURATION_SECONDS.labels(agent_id=str(agent_id), tool_name=tool_name).observe(duration_ms / 1000.0)
        await self._record_timeline_event(run_id, "tool.called", {
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "success": success
        })

    async def record_memory_op(self, agent_id: uuid.UUID, run_id: uuid.UUID, operation: str, latency_ms: float):
        metrics.LLM_AGENT_MEMORY_LATENCY_SECONDS.labels(agent_id=str(agent_id), operation=operation).observe(latency_ms / 1000.0)
        await self._record_timeline_event(run_id, f"memory.{operation}", {"latency_ms": latency_ms})

    async def record_handoff(self, agent_id: uuid.UUID, target_agent_id: uuid.UUID, run_id: uuid.UUID):
        metrics.LLM_AGENT_HANDOFF_COUNT.labels(agent_id=str(agent_id), target_agent_id=str(target_agent_id)).inc()
        await self._record_timeline_event(run_id, "handoff.started", {"target_agent_id": str(target_agent_id)})

    async def record_policy_denial(self, agent_id: uuid.UUID, run_id: uuid.UUID, tool_name: str):
        metrics.LLM_AGENT_POLICY_DENIALS_TOTAL.labels(agent_id=str(agent_id), tool_name=tool_name).inc()
        await self._record_timeline_event(run_id, "policy.denied", {"tool_name": tool_name})

    async def record_cost(self, agent_id: uuid.UUID, run_id: uuid.UUID, cost_brl: float, prompt_tokens: int, completion_tokens: int):
        metrics.LLM_AGENT_COST_BRL_TOTAL.labels(agent_id=str(agent_id)).inc(cost_brl)
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="prompt").inc(prompt_tokens)
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="completion").inc(completion_tokens)

    async def _record_timeline_event(self, run_id: uuid.UUID, event_type: str, details: Dict[str, Any]):
        # Redact secrets
        details_sanitized = self._sanitize_payload(details)
        
        event = AgentTimelineEvent(
            run_id=run_id,
            event_type=event_type,
            details_json=details_sanitized,
            event_time=utc_now()
        )
        self.db.add(event)
        # We don't commit here, let the caller commit or do it in bulk

    def _sanitize_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {k: self._sanitize_payload(v) for k, v in payload.items() if "prompt" not in k.lower()}
        if isinstance(payload, str):
            for secret in ["SECRET_", "KEY_", "TOKEN_"]:
                if secret in payload:
                    return "[REDACTED]"
        return payload

    def _hash_tenant(self, tenant_id: str) -> str:
        return hashlib.sha256(tenant_id.encode()).hexdigest()[:16]
