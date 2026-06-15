# Owner: agent-platform
import time


class AgentRateLimitService:
    """
    Enforces rate limits for agent service invocations.
    In production, this would use Redis for distributed limiting.
    """

    def __init__(self):
        # In-memory mock for now: {tenant_id: [timestamps]}
        self._cache = {}

    async def check_rate_limit(self, tenant_id: str, limit_per_minute: int) -> bool:
        now = time.time()
        minute_ago = now - 60

        if tenant_id not in self._cache:
            self._cache[tenant_id] = []

        # Clean old timestamps
        self._cache[tenant_id] = [t for t in self._cache[tenant_id] if t > minute_ago]

        if len(self._cache[tenant_id]) >= limit_per_minute:
            return False

        self._cache[tenant_id].append(now)
        return True
