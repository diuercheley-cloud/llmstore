# Owner: agent-platform
class Neo4jGraphProvider:
    def __init__(self, enabled: bool):
        if not enabled:
            raise RuntimeError("Neo4j graph provider is disabled by feature flag")

    async def healthcheck(self) -> dict[str, str]:
        return {"status": "configured", "provider": "neo4j"}
