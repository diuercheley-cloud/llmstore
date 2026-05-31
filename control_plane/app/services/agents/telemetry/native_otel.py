import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AgentTracer:
    def __init__(self):
        self.tracer = trace.get_tracer("agent.runtime", "2.0.0")

    def start_agent_span(self, agent_name: str, run_id: str):
        if not settings.agent_otel_tracing_enabled:
            return trace.INVALID_SPAN
            
        return self.tracer.start_as_current_span(
            f"agent.{agent_name}.run",
            attributes={
                "gen_ai.system": "llm-inference-stack",
                "gen_ai.agent.name": agent_name,
                "gen_ai.run.id": run_id,
                "tenant.id": "production"
            }
        )

    def record_thought(self, span, thought: str):
        if span.is_recording():
            span.add_event("thought", {"gen_ai.thought": thought})

    def record_error(self, span, error: Exception):
        if span.is_recording():
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.record_exception(error)

agent_tracer = AgentTracer()
