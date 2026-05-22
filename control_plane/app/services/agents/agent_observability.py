import uuid
import logging
import hashlib
from typing import Any, Dict, Optional, List
from app.core import metrics
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class AgentObservabilityService:
    def __init__(self):
        self.settings = get_settings()

    def _hash_tenant(self, tenant_id: str) -> str:
        if not tenant_id:
            return "unknown"
        # For trace export, we hash the tenant ID to protect privacy
        return hashlib.sha256(tenant_id.encode()).hexdigest()[:12]

    def record_run_started(self, agent_id: str, tenant_id: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status="started").inc()
        logger.info(f"Agent run started: agent={agent_id} tenant={self._hash_tenant(tenant_id)}")

    def record_run_status(self, agent_id: str, status: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_RUNS_TOTAL.labels(agent_id=str(agent_id), status=status).inc()

    def record_run_failure(self, agent_id: str, reason: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_RUN_FAILURES_TOTAL.labels(agent_id=str(agent_id), reason=reason[:32]).inc()

    def record_step(self, agent_id: str, step_type: str, latency_ms: int, status: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_STEPS_TOTAL.labels(agent_id=str(agent_id), step_type=step_type).inc()
        metrics.LLM_AGENT_STEP_LATENCY_SECONDS.labels(agent_id=str(agent_id), step_type=step_type).observe(latency_ms / 1000.0)

    def record_tool_call(self, agent_id: str, tool_name: str, latency_ms: int, success: bool, error_type: Optional[str] = None):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_TOOL_CALLS_TOTAL.labels(agent_id=str(agent_id), tool_name=tool_name).inc()
        if not success:
            metrics.LLM_AGENT_TOOL_FAILURES_TOTAL.labels(
                agent_id=str(agent_id), tool_name=tool_name, error_type=error_type or "execution_error"
            ).inc()

    def record_approval_wait(self, agent_id: str, tool_name: str, wait_seconds: float):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_APPROVAL_WAIT_SECONDS.labels(agent_id=str(agent_id), tool_name=tool_name).observe(wait_seconds)

    def record_policy_denial(self, agent_id: str, tool_name: str):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_POLICY_DENIALS_TOTAL.labels(agent_id=str(agent_id), tool_name=tool_name).inc()

    def record_memory_operation(self, agent_id: str, operation: str):
        if not self.settings.agent_observability_enabled:
            return
        if operation == "read":
            metrics.LLM_AGENT_MEMORY_READS_TOTAL.labels(agent_id=str(agent_id)).inc()
        elif operation == "write":
            metrics.LLM_AGENT_MEMORY_WRITES_TOTAL.labels(agent_id=str(agent_id)).inc()

    def record_tokens(self, agent_id: str, prompt_tokens: int, completion_tokens: int):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="input").inc(prompt_tokens)
        metrics.LLM_AGENT_TOKENS_TOTAL.labels(agent_id=str(agent_id), token_type="output").inc(completion_tokens)

    def record_cost(self, agent_id: str, cost_brl: float):
        if not self.settings.agent_observability_enabled:
            return
        metrics.LLM_AGENT_COST_ESTIMATED_BRL_TOTAL.labels(agent_id=str(agent_id)).inc(cost_brl)

    def get_trace_attributes(self, run: Any, step: Optional[Any] = None) -> Dict[str, Any]:
        """
        Returns a dictionary of attributes following GenAI/Agentic OTel conventions.
        """
        attrs = {
            "agent.id": str(run.agent_id),
            "agent.run_id": str(run.id),
            "tenant.id": self._hash_tenant(run.tenant_id) if self.settings.agent_trace_export_enabled else run.tenant_id,
        }
        
        if hasattr(run, "agent") and run.agent:
            attrs["agent.name"] = run.agent.name
            attrs["agent.version"] = run.agent.version

        if step:
            attrs["agent.step_id"] = str(step.id)
            attrs["agent.step_type"] = step.step_type
            attrs["agent.step_number"] = step.step_number
            
            if step.step_type == "tool_call" and "tool_name" in (step.input_data or {}):
                attrs["tool.name"] = step.input_data["tool_name"]
            
            if step.error:
                attrs["error.message"] = step.error

        return attrs

    def summarize_tool_output(self, output: Any) -> str:
        """Summarizes tool output for observability logs to avoid huge payloads."""
        if isinstance(output, str):
            if len(output) > 500:
                return output[:497] + "..."
            return output
        if isinstance(output, dict):
            # If it's a large dict, maybe just show keys
            if len(str(output)) > 500:
                return f"Dict with keys: {list(output.keys())}"
        return str(output)
