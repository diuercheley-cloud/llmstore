# Owner: agent-platform
class OTelSemconvMapper:
    def map_run(self, run_id: str, agent_id: str, tenant_id: str | None = None) -> dict:
        return {
            "span.name": "agent.run",
            "agent.run_id": run_id,
            "agent.id": agent_id,
            "tenant.id": tenant_id,
        }
