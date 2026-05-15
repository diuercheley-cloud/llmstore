import asyncio
import logging
import uuid

from app.api.deps import get_backend_slot_manager, get_inference_proxy
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import ASYNC_QUEUE_DEPTH
from app.db.session import SessionLocal, engine, redis_client
from app.services.generation_jobs import process_generation_job
from app.services.seed import seed_defaults

configure_logging()
logger = logging.getLogger(__name__)


async def _run_once() -> None:
    settings = get_settings()
    
    job_id = None
    
    # Try QoS Priority Queue if enabled and active
    if settings.commercial_qos_priority_queue_enabled and settings.commercial_qos_priority_queue_mode == "active":
        from app.services.routing.qos_priority_queue import QoSPriorityQueue
        pq = QoSPriorityQueue(redis_client)
        
        # Periodic aging (QoSPriorityQueue.apply_aging handles its own interval internally)
        await pq.apply_aging()
        
        job_id = await pq.dequeue()
        if job_id is None:
            # Record metrics for empty queue
            ASYNC_QUEUE_DEPTH.set(0)
            await asyncio.sleep(1.0) # Short sleep if empty to avoid tight loop
            return
            
        ASYNC_QUEUE_DEPTH.set(await pq.get_queue_depth())
    else:
        # Legacy list-based queue
        item = await redis_client.blpop(settings.async_job_queue_name, timeout=settings.async_worker_block_seconds)
        if item is None:
            ASYNC_QUEUE_DEPTH.set(int(await redis_client.llen(settings.async_job_queue_name)))
            return
        _, raw_job_id = item
        ASYNC_QUEUE_DEPTH.set(int(await redis_client.llen(settings.async_job_queue_name)))
        try:
            job_id = uuid.UUID(raw_job_id)
        except ValueError:
            logger.warning("discarding invalid job id from redis queue", extra={"extra_data": {"job_id": raw_job_id}})
            return

    # Process the job
    async with SessionLocal() as session:
        result = await process_generation_job(session, job_id, get_inference_proxy(), get_backend_slot_manager())
        if result == "requeue":
            # Re-enqueue logic needs to respect priority queue too
            if settings.commercial_qos_priority_queue_enabled:
                from app.services.generation_jobs import enqueue_generation_job
                # We need to fetch the job to get its priority, but process_generation_job 
                # might have already fetched it. For simplicity, we'll use default or fetch.
                # In active mode, we should ideally put it back in the sorted set.
                from app.models.generation_job import GenerationJob
                job = await session.get(GenerationJob, job_id)
                if job:
                    await redis_client.zadd("generation_jobs:priority", {str(job_id): float(job.effective_priority or 0)})
            else:
                await redis_client.rpush(settings.async_job_queue_name, str(job_id))
            
            ASYNC_QUEUE_DEPTH.set(int(await redis_client.llen(settings.async_job_queue_name)))
            await asyncio.sleep(0.5)


async def main() -> None:
    async with SessionLocal() as session:
        await seed_defaults(session)
        await session.commit()
    while True:
        await _run_once()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        try:
            asyncio.run(get_inference_proxy().close())
        except RuntimeError:
            pass
        try:
            asyncio.run(redis_client.aclose())
        except RuntimeError:
            pass
        try:
            asyncio.run(engine.dispose())
        except RuntimeError:
            pass
