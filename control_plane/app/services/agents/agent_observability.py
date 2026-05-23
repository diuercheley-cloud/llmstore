# Owner: agent-platform
import uuid
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import metrics
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentTraceSpan, AgentTimelineEvent
from app.services.agents import agent_state

logger = logging.getLogger(__name__)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

class AgentObservabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def record_run_start(self, agent_id: uuid.UUID, run_id: uuid.UUID, tenant_id: str):
        if not self.settings.agent_observability_enabled:
            return
        
        hashed_tenant = self._hash_tenant(tenant_id)
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status="started").inc()
        await agent_state.log_run_event(self.db, run_id, "run_started", {"tenant_hash": hashed_tenant, "started_at": utc_now().isoformat()})

    async def record_run_completion(self, agent_id: uuid.UUID, run_id: uuid.UUID):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status="completed").inc()
        metrics.LLM_AGENT_RUN_SUCCESS_RATE.labels(agent_id=str(agent_id)).set(1.0)
        
        # Calculate and record run duration
        run = await agent_state.get_agent_run(self.db, run_id)
        if run and run.started_at:
            started_at = _as_utc_aware(run.started_at)
            duration = (utc_now() - started_at).total_seconds()
            metrics.LLM_AGENT_RUN_DURATION_SECONDS.labels(agent_id=str(agent_id)).observe(duration)
            
        await agent_state.log_run_event(self.db, run_id, "run_completed", {"completed_at": utc_now().isoformat()})

    async def record_run_failure(self, agent_id: uuid.UUID, run_id: uuid.UUID, reason: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status="failed").inc()
        metrics.LLM_AGENT_RUN_FAILURES_TOTAL.labels(agent_id=str(agent_id), reason=reason).inc()
        metrics.LLM_AGENT_RUN_SUCCESS_RATE.labels(agent_id=str(agent_id)).set(0.0)
        await agent_state.log_run_event(self.db, run_id, "run_failed", {"failure_reason": reason})

    async def record_step_start(self, run_id: uuid.UUID, step_number: int, step_type: str):
        await agent_state.log_run_event(self.db, run_id, "step_started", {"step_number": step_number, "step_type": step_type})

    async def record_model_call(self, run_id: uuid.UUID, status: str, latency_ms: float, usage: Optional[Dict] = None, error: Optional[str] = None):
        event_type = f"model_call_{status}"
        payload = {"latency_ms": latency_ms}
        if usage: payload["usage"] = usage
        if error: payload["error"] = error
        await agent_state.log_run_event(self.db, run_id, event_type, payload)

    async def record_tool_call_start(self, run_id: uuid.UUID, tool_name: str):
        await agent_state.log_run_event(self.db, run_id, "tool_call_started", {"tool_name": tool_name})

    async def record_tool_call_result(self, run_id: uuid.UUID, tool_name: str, status: str, latency_ms: float, error: Optional[str] = None):
        event_type = f"tool_call_{status}"
        
        # Update metrics if agent_id is available in context or from DB
        run = await agent_state.get_agent_run(self.db, run_id)
        if run:
            agent_id_str = str(run.agent_id)
            metrics.LLM_AGENT_TOOL_LATENCY_SECONDS.labels(agent_id=agent_id_str, tool_name=tool_name).observe(latency_ms / 1000.0)
            metrics.LLM_AGENT_TOOL_FAILURE_RATE.labels(agent_id=agent_id_str, tool_name=tool_name).set(1.0 if status == "failed" else 0.0)
            await agent_state.increment_run_metric(self.db, run_id, "tool_calls_count", 1.0)

        await agent_state.log_run_event(self.db, run_id, event_type, {"tool_name": tool_name, "latency_ms": latency_ms, "error": error})

    async def record_memory_op_detailed(self, run_id: uuid.UUID, op: str, memory_type: str, success: bool):
        if op == "read":
            run = await agent_state.get_agent_run(self.db, run_id)
            if run:
                metrics.LLM_AGENT_MEMORY_HIT_RATE.labels(agent_id=str(run.agent_id), memory_type=memory_type).set(1.0 if success else 0.0)
                await agent_state.increment_run_metric(self.db, run_id, "memory_reads_count", 1.0)
        
        await agent_state.log_run_event(self.db, run_id, f"memory_{op}", {"memory_type": memory_type, "success": success})

    async def record_policy_decision(self, run_id: uuid.UUID, decision: str, reason: str):
        await agent_state.log_run_event(self.db, run_id, "policy_decision", {"decision": decision, "reason": reason})

    async def record_replan(self, run_id: uuid.UUID, reason: str):
        run = await agent_state.get_agent_run(self.db, run_id)
        if run:
            metrics.LLM_AGENT_REPLAN_TOTAL.labels(agent_id=str(run.agent_id)).inc()
            await agent_state.increment_run_metric(self.db, run_id, "replans_count", 1.0)
            
        await agent_state.log_run_event(self.db, run_id, "replan_requested", {"replan_reason": reason})

    async def record_approval_request(self, run_id: uuid.UUID, tool_name: str, reason: str):
        await agent_state.log_run_event(self.db, run_id, "approval_required", {"tool_name": tool_name, "reason": reason})

    async def record_plan_depth(self, agent_id: uuid.UUID, run_id: uuid.UUID, depth: int):
        metrics.LLM_AGENT_PLAN_DEPTH.labels(agent_id=str(agent_id), run_id=str(run_id)).set(depth)
        await agent_state.log_run_event(self.db, run_id, "plan_depth_updated", {"depth": depth})

    def get_trace_attributes(self, run: Any, step: Any = None) -> Dict[str, Any]:
        tenant_val = self._hash_tenant(run.tenant_id) if self.settings.agent_trace_export_enabled else run.tenant_id
        if step is None:
            attrs = {
                "agent_id": str(run.agent_id),
                "tenant_id": tenant_val,
                "status": run.status,
                "total_steps": run.total_steps,
                "total_tokens": run.total_tokens,
                "estimated_cost_brl": run.estimated_cost_brl,
            }
            if run.correlation_id:
                attrs["correlation_id"] = run.correlation_id
            return attrs
        else:
            attrs = {
                "step_number": step.step_number,
                "step_type": step.step_type,
                "status": step.status,
                "latency_ms": step.latency_ms,
            }
            return attrs

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
        
        # Trace handoff depth
        run = await agent_state.get_agent_run(self.db, run_id)
        if run:
            depth = (run.metadata or {}).get("handoff_depth", 0) + 1
            metrics.LLM_AGENT_HANDOFF_DEPTH.labels(agent_id=str(agent_id), run_id=str(run_id)).set(depth)
            
        await self._record_timeline_event(run_id, "handoff.started", {"target_agent_id": str(target_agent_id)})

    async def record_policy_denial(self, agent_id: uuid.UUID, run_id: uuid.UUID, tool_name: str):
        metrics.LLM_AGENT_POLICY_DENIALS_TOTAL.labels(agent_id=str(agent_id), tool_name=tool_name).inc()
        await self._record_timeline_event(run_id, "policy.denied", {"tool_name": tool_name})

    async def record_approval_wait(self, agent_id: uuid.UUID, run_id: uuid.UUID, tool_name: str, wait_time_seconds: float):
        metrics.LLM_AGENT_APPROVAL_WAIT_SECONDS.labels(agent_id=str(agent_id), tool_name=tool_name).observe(wait_time_seconds)
        await agent_state.increment_run_metric(self.db, run_id, "approval_wait_seconds", wait_time_seconds)

    async def record_cost(self, agent_id: uuid.UUID, run_id: uuid.UUID, cost_brl: float, prompt_tokens: int, completion_tokens: int):
        metrics.LLM_AGENT_COST_BRL_TOTAL.labels(agent_id=str(agent_id)).inc(cost_brl)
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="prompt").inc(prompt_tokens)
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="completion").inc(completion_tokens)
        
        # Update budget usage
        metrics.LLM_AGENT_TOKEN_BUDGET_USED.labels(agent_id=str(agent_id)).set(prompt_tokens + completion_tokens)
        metrics.LLM_AGENT_COST_BUDGET_USED_BRL.labels(agent_id=str(agent_id)).set(cost_brl)

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
