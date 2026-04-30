import asyncio
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.metrics import ACTIVE_GENERATIONS, QUEUE_DEPTH


class QueueOverloaded(Exception):
    pass


class QueueTimeout(Exception):
    pass


class QueueManager:
    def __init__(self, backend_slot_manager) -> None:
        settings = get_settings()
        self.max_queue_size = settings.max_queue_size
        self.queue_timeout_seconds = settings.queue_timeout_seconds
        self.pending = 0
        self.lock = asyncio.Lock()
        self.backend_slot_manager = backend_slot_manager

    @asynccontextmanager
    async def slot(self, backend_id=None):
        async with self.lock:
            if self.pending >= self.max_queue_size:
                raise QueueOverloaded("generation queue is full")
            self.pending += 1
            QUEUE_DEPTH.set(self.pending)
        try:
            if backend_id is not None:
                await self.backend_slot_manager.acquire(backend_id, self.queue_timeout_seconds)
            ACTIVE_GENERATIONS.inc()
            try:
                yield
            finally:
                ACTIVE_GENERATIONS.dec()
                if backend_id is not None:
                    await self.backend_slot_manager.release(backend_id)
        finally:
            async with self.lock:
                self.pending = max(0, self.pending - 1)
                QUEUE_DEPTH.set(self.pending)
