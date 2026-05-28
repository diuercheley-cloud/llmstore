# Owner: agent-platform
class FalkorDBGraphProvider:
    def __init__(self, enabled: bool):
        if not enabled:
            raise RuntimeError("FalkorDB graph provider is disabled by feature flag")

    async def healthcheck(self) -> dict[str, str]:
        return {"status": "configured", "provider": "falkordb"}
