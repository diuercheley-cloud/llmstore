# Owner: agent-platform
import math
from datetime import datetime, timedelta

from app.core.time import utc_now


class EventRetryPolicy:
    """
    Manages retry logic and backoff for event delivery.
    """

    def __init__(self, max_retries: int = 5, initial_delay: int = 60):
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    def get_next_retry_at(self, retry_count: int) -> datetime:
        """
        Calculates the next retry timestamp using exponential backoff.
        """
        delay = self.initial_delay * math.pow(2, retry_count)
        return utc_now() + timedelta(seconds=int(delay))

    def should_retry(self, retry_count: int) -> bool:
        return retry_count < self.max_retries
