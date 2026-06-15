# Owner: agent-platform
import time
from typing import Any


class RateLimitManager:
    """
    Manages rate limits for SaaS connectors per tenant and provider.
    """

    def __init__(self):
        self._history = {}  # In-memory history for demonstration; use Redis in production

    def check_rate_limit(self, tenant_id: str, provider: str, policy: dict[str, Any]) -> bool:
        """
        Simple leaky bucket or window-based rate limiting.
        """
        key = f"{tenant_id}:{provider}"
        now = time.time()

        limit = policy.get("requests_per_minute", 60)

        if key not in self._history:
            self._history[key] = []

        # Clean up old requests
        self._history[key] = [t for t in self._history[key] if now - t < 60]

        if len(self._history[key]) >= limit:
            return False

        self._history[key].append(now)
        return True


rate_limit_manager = RateLimitManager()
