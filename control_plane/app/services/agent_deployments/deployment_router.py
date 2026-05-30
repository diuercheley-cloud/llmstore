# Owner: agent-platform
import time
import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_deployments import AgentApiDeployment, AgentApiUsageEvent
from app.core.time import utc_now

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
        minute_ago = now - 60
        if minute_key not in self._rate_counters:
            self._rate_counters[minute_key] = []
        self._rate_counters[minute_key] = [
            t for t in self._rate_counters[minute_key] if t > minute_ago
        ]
        if len(self._rate_counters[minute_key]) >= deployment.rate_limit_per_minute:
            return False

        # Per-day check
        day_key = self._rate_key(str(deployment.id), "day")
        day_ago = now - 86400
        if day_key not in self._rate_counters:
            self._rate_counters[day_key] = []
        self._rate_counters[day_key] = [
            t for t in self._rate_counters[day_key] if t > day_ago
        ]
        if len(self._rate_counters[day_key]) >= deployment.rate_limit_per_day:
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
