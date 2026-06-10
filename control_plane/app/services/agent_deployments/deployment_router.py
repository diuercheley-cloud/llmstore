# Owner: agent-platform
import logging
import time
from typing import Dict

from app.models.agents.agent_deployments import AgentApiDeployment

logger = logging.getLogger(__name__)


class DeploymentRateLimitError(Exception):
    pass


class DeploymentConcurrencyError(Exception):
    pass


class DeploymentRouter:
    """
    Resolves deployment slugs, enforces rate limits and concurrency.
    Uses in-memory counters (Redis in production).
    """

    def __init__(self):
        self._rate_counters: Dict[str, list] = {}  # key -> [timestamps]
        self._concurrency_counters: Dict[str, int] = {}  # deployment_id -> count

    def _rate_key(self, deployment_id: str, window: str = "minute") -> str:
        return f"rate:{deployment_id}:{window}"

    def check_rate_limit(self, deployment: AgentApiDeployment) -> bool:
        """Check if deployment is within rate limits. Returns True if allowed."""
        now = time.time()

        # Per-minute check
        minute_key = self._rate_key(str(deployment.id), "minute")
        minute_limit = deployment.rate_limit_per_minute or 60
        minute_ago = now - 60
        if minute_key not in self._rate_counters:
            self._rate_counters[minute_key] = []
        self._rate_counters[minute_key] = [
            t for t in self._rate_counters[minute_key] if t > minute_ago
        ]
        if len(self._rate_counters[minute_key]) >= minute_limit:
            return False

        # Per-day check
        day_key = self._rate_key(str(deployment.id), "day")
        day_limit = deployment.rate_limit_per_day or 10000
        day_ago = now - 86400
        if day_key not in self._rate_counters:
            self._rate_counters[day_key] = []
        self._rate_counters[day_key] = [
            t for t in self._rate_counters[day_key] if t > day_ago
        ]
        if len(self._rate_counters[day_key]) >= day_limit:
            return False

        # Record this request
        self._rate_counters[minute_key].append(now)
        self._rate_counters[day_key].append(now)
        return True

    def acquire_concurrency(self, deployment: AgentApiDeployment) -> bool:
        """Try to acquire a concurrency slot. Returns True if acquired."""
        key = str(deployment.id)
        current = self._concurrency_counters.get(key, 0)
        if current >= deployment.max_concurrency:
            return False
        self._concurrency_counters[key] = current + 1
        return True

    def release_concurrency(self, deployment_id: str):
        """Release a concurrency slot."""
        key = str(deployment_id)
        current = self._concurrency_counters.get(key, 0)
        if current > 0:
            self._concurrency_counters[key] = current - 1

    def get_concurrent_count(self, deployment_id: str) -> int:
        return self._concurrency_counters.get(str(deployment_id), 0)

    def get_rate_usage(self, deployment_id: str) -> Dict[str, int]:
        """Get current rate usage for a deployment."""
        now = time.time()
        minute_key = self._rate_key(str(deployment_id), "minute")
        day_key = self._rate_key(str(deployment_id), "day")
        return {
            "requests_this_minute": len(self._rate_counters.get(minute_key, [])),
            "requests_today": len(self._rate_counters.get(day_key, [])),
        }


# Global singleton
deployment_router = DeploymentRouter()
