import json
import uuid
import logging
import asyncio
from datetime import timedelta
from typing import List, Optional, Dict, Any
from redis.asyncio import Redis
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class RedisAgentQueue:
    """
    Redis-backed distributed task queue for agent execution.
    Uses sorted sets for priority and streams for reliable delivery.
    """
    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()
        self.queue_key = "agent:queue:jobs"
        self.lease_key_prefix = "agent:lease:"

    async def enqueue_job(
        self,
        agent_run_id: uuid.UUID,
        agent_id: uuid.UUID,
        tenant_id: str,
        priority: int = 0,
        **kwargs
    ) -> str:
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "agent_run_id": str(agent_run_id),
            "agent_id": str(agent_id),
            "tenant_id": tenant_id,
            "priority": priority,
            "created_at": utc_now().isoformat(),
            **kwargs
        }
        
        # Add to sorted set with priority as score
        # Using negative priority so higher values come first
        await self.redis.zadd(self.queue_key, {json.dumps(job_data): -priority})
        
        logger.info(f"Redis Enqueued job {job_id} for run {agent_run_id} (priority: {priority})")
        return job_id

    async def dequeue_job(self, worker_id: str, lease_timeout_seconds: int = 60) -> Optional[Dict[str, Any]]:
        # Get the highest priority job (lowest score in ZSET because we used negative priority)
        jobs = await self.redis.zrange(self.queue_key, 0, 0)
        if not jobs:
            return None
            
        job_raw = jobs[0]
        # Atomic removal
        removed = await self.redis.zrem(self.queue_key, job_raw)
        if not removed:
            # Another worker got it first
            return None
            
        job = json.loads(job_raw)
        job_id = job["id"]
        
        # Set lease
        lease_key = f"{self.lease_key_prefix}{job_id}"
        await self.redis.set(lease_key, worker_id, ex=lease_timeout_seconds)
        
        logger.info(f"Worker {worker_id} leased job {job_id} from Redis")
        return job

    async def complete_job(self, job_id: str):
        await self.redis.delete(f"{self.lease_key_prefix}{job_id}")
