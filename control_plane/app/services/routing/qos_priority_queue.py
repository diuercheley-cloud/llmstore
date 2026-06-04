import logging
import time
import uuid
from typing import Optional

from app.core.config import get_settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class QoSPriorityQueue:
    """
    Manages a priority queue for generation jobs using Redis Sorted Sets.
    
    Score calculation:
    score = -(priority_weight * 1,000,000) + created_at_ms + aging_adjustment
    
    Lower score = Higher priority (processed first).
    """
    
    QUEUE_KEY = "generation_jobs:priority"
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()

    def _calculate_score(
        self, 
        priority_weight: int, 
        created_at_ms: int, 
        aging_adjustment: float = 0
    ) -> float:
        # Lower score = higher priority
        return -(priority_weight * 1_000_000) + created_at_ms + aging_adjustment

    async def enqueue(
        self, 
        job_id: uuid.UUID, 
        priority_weight: int, 
        created_at_ms: Optional[int] = None
    ) -> float:
        if created_at_ms is None:
            created_at_ms = int(time.time() * 1000)
            
        score = self._calculate_score(priority_weight, created_at_ms)
        
        # Add to sorted set
        await self.redis.zadd(self.QUEUE_KEY, {str(job_id): score})
        
        # Record metrics if needed
        return score

    async def dequeue(self) -> Optional[uuid.UUID]:
        # ZPOPMIN gets the item with the lowest score
        result = await self.redis.zpopmin(self.QUEUE_KEY)
        if not result:
            return None
            
        job_id_str, score = result[0]
        try:
            return uuid.UUID(job_id_str.decode() if isinstance(job_id_str, bytes) else job_id_str)
        except ValueError:
            logger.error(f"Invalid job ID in priority queue: {job_id_str}")
            return None

    async def peek(self) -> Optional[uuid.UUID]:
        result = await self.redis.zrange(self.QUEUE_KEY, 0, 0)
        if not result:
            return None
        return uuid.UUID(result[0].decode() if isinstance(result, bytes) else result[0])

    async def get_queue_depth(self) -> int:
        return await self.redis.zcard(self.QUEUE_KEY)

    async def apply_aging(self):
        """
        Adjust scores of waiting jobs to prevent starvation.
        For every COMMERCIAL_QOS_QUEUE_AGING_SECONDS a job waits,
        it gets an aging_adjustment that reduces its score (increases priority).
        
        We use a Lua script to update scores in place.
        """
        aging_seconds = self.settings.commercial_qos_queue_aging_seconds
        if not aging_seconds or aging_seconds <= 0:
            return

        # Reduction of 100,000 (0.1 priority level) per aging interval
        aging_step = 100000 
        
        lua_script = """
        local queue_key = KEYS[1]
        local aging_step = tonumber(ARGV[1])
        
        local jobs = redis.call('ZRANGE', queue_key, 0, -1, 'WITHSCORES')
        for i=1, #jobs, 2 do
            local job_id = jobs[i]
            local score = tonumber(jobs[i+1])
            redis.call('ZADD', queue_key, score - aging_step, job_id)
        end
        return #jobs / 2
        """
        
        # We only apply this periodically. The caller should manage the interval.
        # Or we can check a last_aging_timestamp in Redis.
        last_aging = await self.redis.get("qos_queue:last_aging_ts")
        now = time.time()
        if last_aging and now - float(last_aging) < aging_seconds:
            return
            
        await self.redis.eval(lua_script, 1, self.QUEUE_KEY, aging_step)
        await self.redis.set("qos_queue:last_aging_ts", str(now))
        logger.info(f"Applied aging to QoS priority queue, step={aging_step}")

    async def get_stats(self) -> dict:
        depth = await self.get_queue_depth()
        if depth == 0:
            return {"depth": 0}
            
        # Get oldest and newest to see spread
        first = await self.redis.zrange(self.QUEUE_KEY, 0, 0, withscores=True)
        last = await self.redis.zrange(self.QUEUE_KEY, -1, -1, withscores=True)
        
        return {
            "depth": depth,
            "oldest_score": first[0][1] if first else None,
            "newest_score": last[0][1] if last else None,
        }
