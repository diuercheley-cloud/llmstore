import logging
import time
import uuid
from typing import Optional, Tuple

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class QoSRateLimiter:
    """
    Advanced rate limiter per QoS tier.
    Uses sliding window algorithm in Redis.
    """
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()

    def _get_limit_for_tier(self, tier_name: str) -> int:
        tier_name = tier_name.lower()
        if tier_name == "free":
            return self.settings.commercial_qos_free_rpm
        if tier_name == "basic":
            return self.settings.commercial_qos_basic_rpm
        if tier_name == "pro":
            return self.settings.commercial_qos_pro_rpm
        if tier_name == "premium":
            return self.settings.commercial_qos_premium_rpm
        if tier_name == "enterprise":
            return self.settings.commercial_qos_enterprise_rpm
        return self.settings.commercial_qos_basic_rpm

    async def check_rate_limit(
        self, 
        client_id: uuid.UUID, 
        qos_tier: str,
        model_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Checks if a request should be rate limited.
        Returns (is_allowed, status, reason)
        """
        if not self.settings.commercial_qos_rate_limiting_enabled:
            return True, "allowed", None

        limit_rpm = self._get_limit_for_tier(qos_tier)
        if limit_rpm <= 0:
            return True, "allowed", None

        now = time.time()
        window_start = now - 60
        
        # Keys for different granularity
        client_key = f"qos_rl:client:{client_id}:rpm"
        tier_key = f"qos_rl:tier:{qos_tier}:rpm"
        
        # Sliding window using Sorted Set
        async with self.redis.pipeline() as pipe:
            # Clean up old requests
            pipe.zremrangebyscore(client_key, 0, window_start)
            # Count current requests in window
            pipe.zcard(client_key)
            # Add current request
            pipe.zadd(client_key, {str(now): now})
            # Set expiry for the key
            pipe.expire(client_key, 70)
            
            results = await pipe.execute()
            
        current_rpm = results[1]
        
        if current_rpm >= limit_rpm:
            mode = self.settings.commercial_qos_rate_limit_mode
            reason = f"QoS tier '{qos_tier}' limit reached: {current_rpm}/{limit_rpm} RPM"
            
            if mode == "enforce":
                return False, "rejected", reason
            else:
                return True, "throttled", reason
                
        return True, "allowed", None

    async def get_current_rpm(self, client_id: uuid.UUID) -> int:
        client_key = f"qos_rl:client:{client_id}:rpm"
        now = time.time()
        window_start = now - 60
        return await self.redis.zcount(client_key, window_start, now)
