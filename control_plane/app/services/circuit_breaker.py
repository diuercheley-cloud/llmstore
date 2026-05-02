import asyncio
import time

from app.core.config import get_settings
from app.core.metrics import CIRCUIT_BREAKER_STATE


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self) -> None:
        settings = get_settings()
        self.failure_threshold = settings.circuit_breaker_failure_threshold
        self.recovery_seconds = settings.circuit_breaker_recovery_seconds
        self.failures = 0
        self.opened_at = 0.0
        self.lock = asyncio.Lock()

    async def before_call(self) -> None:
        async with self.lock:
            if self.failures < self.failure_threshold:
                CIRCUIT_BREAKER_STATE.set(0)
                return
            if time.monotonic() - self.opened_at >= self.recovery_seconds:
                self.failures = 0
                self.opened_at = 0.0
                CIRCUIT_BREAKER_STATE.set(0)
                return
            CIRCUIT_BREAKER_STATE.set(1)
            raise CircuitBreakerOpen("data plane circuit breaker is open")

    async def record_success(self) -> None:
        async with self.lock:
            self.failures = 0
            self.opened_at = 0.0
            CIRCUIT_BREAKER_STATE.set(0)

    async def record_failure(self) -> None:
        async with self.lock:
            self.failures += 1
            if self.failures >= self.failure_threshold and self.opened_at == 0.0:
                self.opened_at = time.monotonic()
                CIRCUIT_BREAKER_STATE.set(1)

    async def reset(self) -> None:
        async with self.lock:
            self.failures = 0
            self.opened_at = 0.0
            CIRCUIT_BREAKER_STATE.set(0)
