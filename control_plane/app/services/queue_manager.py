import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
import uuid

from app.core.config import get_settings
from app.core.metrics import (
    ACTIVE_GENERATIONS,
    QUEUE_DEPTH,
    QUEUE_WAITING,
    QUEUE_ACTIVE,
    QUEUE_FAILED,
    QUEUE_WAIT_TIME,
    record_queue_wait,
)


class QueueOverloaded(Exception):
    def __init__(self, message, queue_name=None):
        super().__init__(message)
        self.queue_name = queue_name


class QueueTimeout(Exception):
    def __init__(self, message, queue_name=None):
        super().__init__(message)
        self.queue_name = queue_name


class QueueManager:
    def __init__(self, backend_slot_manager) -> None:
        settings = get_settings()
        self.backend_slot_manager = backend_slot_manager
        
        # Logical Queues Configuration
        self.queues = {
            "inference_admin": {
                "max_waiting": settings.queue_admin_max_waiting,
                "max_active": settings.queue_admin_max_active,
                "timeout": settings.queue_admin_timeout,
                "priority": 0,
            },
            "inference_premium": {
                "max_waiting": settings.queue_premium_max_waiting,
                "max_active": settings.queue_premium_max_active,
                "timeout": settings.queue_premium_timeout,
                "priority": 1,
            },
            "inference_basic": {
                "max_waiting": settings.queue_basic_max_waiting,
                "max_active": settings.queue_basic_max_active,
                "timeout": settings.queue_basic_timeout,
                "priority": 2,
            },
            "inference_free": {
                "max_waiting": settings.queue_free_max_waiting,
                "max_active": settings.queue_free_max_active,
                "timeout": settings.queue_free_timeout,
                "priority": 3,
            },
        }
        
        self.waiting_counts = {q: 0 for q in self.queues}
        self.active_counts = {q: 0 for q in self.queues}
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.lock)
        
        # Compatibility with old metrics
        self.pending = 0 
        self.max_queue_size = settings.max_queue_size

    def _resolve_queue_name(self, plan_code: str, is_admin: bool = False) -> str:
        if is_admin:
            return "inference_admin"
        if plan_code in {"pro", "enterprise", "premium"}:
            return "inference_premium"
        if plan_code == "basic":
            return "inference_basic"
        return "inference_free"

    def get_snapshot(self) -> dict:
        return {
            "queues": {
                name: {
                    "waiting": self.waiting_counts[name],
                    "active": self.active_counts[name],
                    "max_waiting": cfg["max_waiting"],
                    "max_active": cfg["max_active"],
                    "priority": cfg["priority"],
                    "timeout": cfg["timeout"],
                }
                for name, cfg in self.queues.items()
            },
            "total_pending": self.pending,
        }

    @asynccontextmanager
    async def slot(self, plan_code: str = "free", is_admin: bool = False, backend_id=None):
        queue_name = self._resolve_queue_name(plan_code, is_admin)
        limits = self.queues[queue_name]
        
        async with self.lock:
            if self.waiting_counts[queue_name] >= limits["max_waiting"]:
                QUEUE_FAILED.labels(queue_name=queue_name, reason="overloaded").inc()
                raise QueueOverloaded(f"generation queue '{queue_name}' is full", queue_name=queue_name)
            
            self.waiting_counts[queue_name] += 1
            self.pending += 1
            QUEUE_WAITING.labels(queue_name=queue_name).set(self.waiting_counts[queue_name])
            QUEUE_DEPTH.set(self.pending)

        wait_start = perf_counter()
        acquired = False
        try:
            deadline = wait_start + limits["timeout"]
            while True:
                can_try = False
                async with self.lock:
                    if self.active_counts[queue_name] < limits["max_active"]:
                        higher_priority_waiting = False
                        for q, cfg in self.queues.items():
                            if cfg["priority"] < limits["priority"] and self.waiting_counts[q] > 0:
                                higher_priority_waiting = True
                                break
                        
                        if not higher_priority_waiting or queue_name == "inference_admin":
                            can_try = True
                
                if can_try:
                    if backend_id is not None:
                        if await self.backend_slot_manager.try_acquire(backend_id):
                            acquired = True
                            break
                    else:
                        acquired = True
                        break
                
                if perf_counter() >= deadline:
                    QUEUE_FAILED.labels(queue_name=queue_name, reason="timeout").inc()
                    raise QueueTimeout(f"timeout waiting for slot in '{queue_name}'", queue_name=queue_name)
                
                # Wait for notification or timeout to retry
                async with self.condition:
                    try:
                        # Shorter wait for higher priority to be more reactive
                        timeout = 0.1 if limits["priority"] <= 1 else 0.4
                        await asyncio.wait_for(self.condition.wait(), timeout=timeout)
                    except asyncio.TimeoutError:
                        pass

            # Successfully acquired slots
            async with self.lock:
                self.waiting_counts[queue_name] -= 1
                self.active_counts[queue_name] += 1
                # self.pending stays same as it tracks both waiting + active for compatibility
                QUEUE_WAITING.labels(queue_name=queue_name).set(self.waiting_counts[queue_name])
                QUEUE_ACTIVE.labels(queue_name=queue_name).set(self.active_counts[queue_name])
                wait_seconds = perf_counter() - wait_start
                QUEUE_WAIT_TIME.labels(queue_name=queue_name).observe(wait_seconds)
                record_queue_wait(plan=plan_code, wait_seconds=wait_seconds)
                ACTIVE_GENERATIONS.inc()

            try:
                yield
            finally:
                async with self.lock:
                    self.active_counts[queue_name] = max(0, self.active_counts[queue_name] - 1)
                    self.pending = max(0, self.pending - 1)
                    QUEUE_ACTIVE.labels(queue_name=queue_name).set(self.active_counts[queue_name])
                    QUEUE_DEPTH.set(self.pending)
                    ACTIVE_GENERATIONS.dec()
                    
                if acquired and backend_id is not None:
                    await self.backend_slot_manager.release(backend_id)
                
                # Notify all waiting tasks that a slot has been freed
                async with self.condition:
                    self.condition.notify_all()
        finally:
            if not acquired:
                async with self.lock:
                    self.waiting_counts[queue_name] = max(0, self.waiting_counts[queue_name] - 1)
                    self.pending = max(0, self.pending - 1)
                    QUEUE_WAITING.labels(queue_name=queue_name).set(self.waiting_counts[queue_name])
                    QUEUE_DEPTH.set(self.pending)
