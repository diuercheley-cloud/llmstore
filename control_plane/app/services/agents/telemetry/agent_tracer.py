# Owner: agent-platform
from .otel_semconv_mapper import OTelSemconvMapper
from .trace_sanitizer import TraceSanitizer


class AgentTracer:
    def __init__(self):
        self.mapper = OTelSemconvMapper()
        self.sanitizer = TraceSanitizer()

    def trace_run(self, run_id: str, agent_id: str, tenant_id: str | None = None) -> dict:
        payload = self.mapper.map_run(run_id, agent_id, tenant_id=self.sanitizer.hash_tenant(tenant_id))
        return payload
