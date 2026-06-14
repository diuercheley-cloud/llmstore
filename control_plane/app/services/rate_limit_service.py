from __future__ import annotations

import logging
import time
import math
from typing import NamedTuple, Optional, Any, Dict
from redis.asyncio import Redis
from fastapi import HTTPException, Response
from app.core.metrics import RATE_LIMIT_EXCEEDED_TOTAL, RATE_LIMIT_LATENCY_SECONDS
from app.core.request_context import get_source_ip

logger = logging.getLogger(__name__)

class RateLimitResult(NamedTuple):
    allowed: bool
    limit: int
    remaining: int
    retry_after: float

class RateLimitService:
    def __init__(self, redis: Redis):
        self.redis = redis
        # Standard GCRA (Generic Cell Rate Algorithm) implementation in Lua
        self._lua_script = """
            local key = KEYS[1]
            local rate = tonumber(ARGV[1])
            local burst = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            local period = burst / rate
            local emission_interval = 1 / rate
            
            local tat = tonumber(redis.call('get', key) or 0)
            
            local new_tat = math.max(tat, now) + emission_interval
            local allow_at = new_tat - period
            
            if now < allow_at then
                return {0, allow_at - now, 0}
            end
            
            redis.call('set', key, new_tat, 'EX', math.ceil(period) + 1)
            local remaining = math.floor((now - allow_at) / emission_interval)
            
            return {1, 0, remaining}
        """

    async def check_rate_limit(
        self,
        tenant_id: str,
        client_id: str,
        endpoint: str,
        limit_per_minute: int
    ) -> RateLimitResult:
        if limit_per_minute <= 0:
            return RateLimitResult(allowed=True, limit=0, remaining=1, retry_after=0)

        start_time = time.perf_counter()
        key = f"rl:{tenant_id}:{client_id}:{endpoint}"
        
        # RPM to rate per second
        rate = limit_per_minute / 60.0
        burst = limit_per_minute
        now = time.time()
        
        try:
            res = await self.redis.eval(self._lua_script, 1, key, rate, burst, now)
            allowed, retry_after, remaining = res
            
            latency = time.perf_counter() - start_time
            labels = {"tenant_id": tenant_id, "client_id": client_id, "endpoint": endpoint}
            RATE_LIMIT_LATENCY_SECONDS.labels(**labels).observe(latency)
            
            if not allowed:
                RATE_LIMIT_EXCEEDED_TOTAL.labels(**labels).inc()
                
            return RateLimitResult(
                allowed=bool(allowed),
                limit=limit_per_minute,
                remaining=int(remaining),
                retry_after=float(retry_after)
            )
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open to avoid blocking users if Redis is down
            return RateLimitResult(allowed=True, limit=limit_per_minute, remaining=1, retry_after=0)


async def apply_api_rate_limit(
    redis: Redis,
    session: Any, # AsyncSession
    client: Any, # Client model
    endpoint: str,
    limit: int,
    response: Response
) -> None:
    """
    Applies rate limiting to an API request, including headers and abuse detection.
    """
    svc = get_rate_limit_service(redis)
    tenant_id = getattr(client, "tenant_id", "default")
    
    res = await svc.check_rate_limit(
        tenant_id=tenant_id,
        client_id=str(client.id),
        endpoint=endpoint,
        limit_per_minute=limit
    )
    
    response.headers["X-RateLimit-Limit"] = str(res.limit)
    response.headers["X-RateLimit-Remaining"] = str(res.remaining)
    
    if not res.allowed:
        response.headers["Retry-After"] = str(math.ceil(res.retry_after))
        
        # Integration with Abuse Detection
        try:
            from app.services.security.abuse_detection import check_rate_limit_abuse
            await check_rate_limit_abuse(
                session=session,
                redis=redis,
                client_id=client.id,
                limit_per_minute=limit,
                current_count=limit + 1,
                source_ip=get_source_ip()
            )
        except Exception as ae:
            logger.error(f"Failed to record rate limit abuse: {ae}")

        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {res.retry_after:.1f} seconds."
        )


_service = None

def get_rate_limit_service(redis: Redis) -> RateLimitService:
    global _service
    if _service is None:
        _service = RateLimitService(redis)
    return _service
