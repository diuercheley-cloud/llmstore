# Owner: agent-platform
import time
from threading import Lock


class LeakyBucket:
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = float(capacity)
        self.leak_rate = leak_rate
        self._water = 0.0
        self._last_time = time.monotonic()
        self._lock = Lock()

    def try_consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            self._water = max(0.0, self._water - self.leak_rate * (now - self._last_time))
            self._last_time = now
            if self._water + tokens <= self.capacity:
                self._water += tokens
                return True
            return False

    @property
    def fill_ratio(self) -> float:
        with self._lock:
            now = time.monotonic()
            self._water = max(0.0, self._water - self.leak_rate * (now - self._last_time))
            self._last_time = now
            return self._water / self.capacity if self.capacity > 0 else 1.0

    def reset(self) -> None:
        with self._lock:
            self._water = 0.0
            self._last_time = time.monotonic()


class LeakyBucketManager:
    def __init__(self):
        self._buckets: dict[str, LeakyBucket] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        key: str,
        capacity: int = 100,
        leak_rate: float = 10.0,
    ) -> LeakyBucket:
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = LeakyBucket(capacity, leak_rate)
            return self._buckets[key]

    def reset_all(self) -> None:
        with self._lock:
            for bucket in self._buckets.values():
                bucket.reset()

    def reset_key(self, key: str) -> None:
        with self._lock:
            if key in self._buckets:
                self._buckets[key].reset()

    def check_quota(
        self,
        tenant_id: str,
        agent_id: str,
        span_type: str,
        exporter: str = "default",
        capacity: int = 100,
        leak_rate: float = 10.0,
    ) -> bool:
        tenant_key = f"tenant:{tenant_id}"
        agent_key = f"agent:{tenant_id}:{agent_id}"
        type_key = f"type:{span_type}"
        exporter_key = f"exporter:{exporter}"

        tenant_bucket = self.get_or_create(tenant_key, capacity * 4, leak_rate * 4)
        agent_bucket = self.get_or_create(agent_key, capacity * 2, leak_rate * 2)
        type_bucket = self.get_or_create(type_key, capacity, leak_rate)
        exporter_bucket = self.get_or_create(exporter_key, capacity * 4, leak_rate * 4)

        return all(
            [
                tenant_bucket.try_consume(),
                agent_bucket.try_consume(),
                type_bucket.try_consume(),
                exporter_bucket.try_consume(),
            ]
        )
