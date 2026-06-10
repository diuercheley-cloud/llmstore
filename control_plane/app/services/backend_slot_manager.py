import asyncio
import uuid
from contextlib import asynccontextmanager
from time import monotonic

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.core.inference_backend import InferenceBackend
from app.services.queue_manager import QueueTimeout
from sqlalchemy import select


class BackendSlotManager:
    def __init__(self, poll_interval_seconds: float = 0.2) -> None:
        self.poll_interval_seconds = poll_interval_seconds

    async def try_acquire(self, backend_id: uuid.UUID) -> bool:
        async with SessionLocal() as session:
            result = await session.execute(
                select(InferenceBackend).where(InferenceBackend.id == backend_id).with_for_update()
            )
            backend = result.scalar_one_or_none()
            if backend is None or not backend.is_active:
                await session.rollback()
                return False
            limit = max(int(backend.max_parallel_requests or 1), 1)
            if int(backend.current_running or 0) >= limit:
                await session.rollback()
                return False
            backend.current_running = int(backend.current_running or 0) + 1
            backend.updated_at = utc_now()
            await session.commit()
            return True

    async def acquire(self, backend_id: uuid.UUID, timeout_seconds: float) -> None:
        deadline = monotonic() + timeout_seconds
        while True:
            if await self.try_acquire(backend_id):
                return
            if monotonic() >= deadline:
                raise QueueTimeout("backend concurrency limit reached")
            await asyncio.sleep(self.poll_interval_seconds)

    async def release(self, backend_id: uuid.UUID) -> None:
        async with SessionLocal() as session:
            result = await session.execute(
                select(InferenceBackend).where(InferenceBackend.id == backend_id).with_for_update()
            )
            backend = result.scalar_one_or_none()
            if backend is None:
                await session.rollback()
                return
            backend.current_running = max(int(backend.current_running or 0) - 1, 0)
            backend.updated_at = utc_now()
            await session.commit()

    @asynccontextmanager
    async def slot(self, backend_id: uuid.UUID, timeout_seconds: float):
        await self.acquire(backend_id, timeout_seconds)
        try:
            yield
        finally:
            await self.release(backend_id)
