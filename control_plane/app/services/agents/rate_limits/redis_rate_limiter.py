import logging
import time

from app.core.config import get_settings
from app.db.session import redis_client

logger = logging.getLogger("redis_rate_limiter")


class LocalRateLimiterFallback:
    """In-memory fallback rate limiter for development or when Redis is disabled."""

    _requests = {}  # (tenant, agent, bucket) -> count
    _concurrent = {}  # (tenant, agent) -> count
    _tools = {}  # (tenant, agent, bucket) -> count
    _cost_hour = {}  # (tenant, agent, bucket) -> cost
    _cost_run = {}  # (tenant, agent, run_id) -> cost

    @classmethod
    def reset(cls):
        cls._requests.clear()
        cls._concurrent.clear()
        cls._tools.clear()
        cls._cost_hour.clear()
        cls._cost_run.clear()

    @classmethod
    def check_request_rate(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        bucket = int(time.time() / 60)
        key = (tenant_id, agent_id, bucket)
        current = cls._requests.get(key, 0)
        if current >= limit:
            return False
        cls._requests[key] = current + 1
        return True

    @classmethod
    def increment_concurrent_runs(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        key = (tenant_id, agent_id)
        current = cls._concurrent.get(key, 0)
        if current >= limit:
            return False
        cls._concurrent[key] = current + 1
        return True

    @classmethod
    def decrement_concurrent_runs(cls, tenant_id: str, agent_id: str):
        key = (tenant_id, agent_id)
        current = cls._concurrent.get(key, 0)
        if current > 0:
            cls._concurrent[key] = current - 1

    @classmethod
    def check_tool_rate(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        bucket = int(time.time() / 60)
        key = (tenant_id, agent_id, bucket)
        current = cls._tools.get(key, 0)
        if current >= limit:
            return False
        cls._tools[key] = current + 1
        return True

    @classmethod
    def check_cost_hour(cls, tenant_id: str, agent_id: str, cost: float, limit: float) -> bool:
        bucket = int(time.time() / 3600)
        key = (tenant_id, agent_id, bucket)
        current = cls._cost_hour.get(key, 0.0)
        if current + cost > limit:
            return False
        cls._cost_hour[key] = current + cost
        return True

    @classmethod
    def check_cost_run(
        cls, tenant_id: str, agent_id: str, run_id: str, cost: float, limit: float
    ) -> bool:
        key = (tenant_id, agent_id, run_id)
        current = cls._cost_run.get(key, 0.0)
        if current + cost > limit:
            return False
        cls._cost_run[key] = current + cost
        return True


class RedisRateLimiter:
    is_fallback_active = False

    @classmethod
    def _use_fallback(cls) -> bool:
        settings = get_settings()
        return not settings.agent_distributed_rate_limiting_enabled

    @classmethod
    async def check_request_rate(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        """Rate limit: requests/minute."""
        if cls._use_fallback():
            cls.is_fallback_active = True
            logger.info("Local rate limiter fallback activated for request rate")
            return LocalRateLimiterFallback.check_request_rate(tenant_id, agent_id, limit)

        cls.is_fallback_active = False
        bucket = int(time.time() / 60)
        key = f"rl:req:{tenant_id}:{agent_id}:{bucket}"

        try:
            current = await redis_client.get(key)
            if current and int(current) >= limit:
                return False

            # Increment and set TTL
            val = await redis_client.incr(key)
            if val == 1:
                await redis_client.expire(key, 120)

            if val > limit:
                return False
            return True
        except Exception as e:
            logger.error(f"Redis rate limiting error, falling back to local: {e}")
            cls.is_fallback_active = True
            return LocalRateLimiterFallback.check_request_rate(tenant_id, agent_id, limit)

    @classmethod
    async def increment_concurrent_runs(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        """Rate limit: concurrent active runs."""
        if cls._use_fallback():
            cls.is_fallback_active = True
            logger.info("Local rate limiter fallback activated for concurrent runs")
            return LocalRateLimiterFallback.increment_concurrent_runs(tenant_id, agent_id, limit)

        cls.is_fallback_active = False
        key = f"rl:concurrent:{tenant_id}:{agent_id}"

        try:
            current = await redis_client.get(key)
            if current and int(current) >= limit:
                return False

            val = await redis_client.incr(key)
            await redis_client.expire(key, 86400)

            if val > limit:
                # Revert increment if exceeded
                await redis_client.decr(key)
                return False
            return True
        except Exception as e:
            logger.error(f"Redis concurrent runs check error, falling back to local: {e}")
            cls.is_fallback_active = True
            return LocalRateLimiterFallback.increment_concurrent_runs(tenant_id, agent_id, limit)

    @classmethod
    async def decrement_concurrent_runs(cls, tenant_id: str, agent_id: str):
        """Decrements concurrent runs counter."""
        if cls._use_fallback():
            LocalRateLimiterFallback.decrement_concurrent_runs(tenant_id, agent_id)
            return

        key = f"rl:concurrent:{tenant_id}:{agent_id}"
        try:
            val = await redis_client.get(key)
            if val and int(val) > 0:
                await redis_client.decr(key)
        except Exception as e:
            logger.error(f"Redis concurrent runs decrement error: {e}")
            LocalRateLimiterFallback.decrement_concurrent_runs(tenant_id, agent_id)

    @classmethod
    async def check_tool_rate(cls, tenant_id: str, agent_id: str, limit: int) -> bool:
        """Rate limit: tool calls/minute."""
        if cls._use_fallback():
            cls.is_fallback_active = True
            logger.info("Local rate limiter fallback activated for tool rate")
            return LocalRateLimiterFallback.check_tool_rate(tenant_id, agent_id, limit)

        cls.is_fallback_active = False
        bucket = int(time.time() / 60)
        key = f"rl:tool:{tenant_id}:{agent_id}:{bucket}"

        try:
            current = await redis_client.get(key)
            if current and int(current) >= limit:
                return False

            val = await redis_client.incr(key)
            if val == 1:
                await redis_client.expire(key, 120)

            if val > limit:
                return False
            return True
        except Exception as e:
            logger.error(f"Redis tool rate limiting error, falling back to local: {e}")
            cls.is_fallback_active = True
            return LocalRateLimiterFallback.check_tool_rate(tenant_id, agent_id, limit)

    @classmethod
    async def check_cost_hour(
        cls, tenant_id: str, agent_id: str, cost: float, limit: float
    ) -> bool:
        """Rate limit: cost/hour."""
        if cls._use_fallback():
            cls.is_fallback_active = True
            logger.info("Local rate limiter fallback activated for cost/hour")
            return LocalRateLimiterFallback.check_cost_hour(tenant_id, agent_id, cost, limit)

        cls.is_fallback_active = False
        bucket = int(time.time() / 3600)
        key = f"rl:cost_hour:{tenant_id}:{agent_id}:{bucket}"

        try:
            current = await redis_client.get(key)
            if current and float(current) + cost > limit:
                return False

            # Use incrbyfloat
            val = await redis_client.incrbyfloat(key, cost)
            await redis_client.expire(key, 7200)

            if val > limit:
                # Revert increment if exceeded
                await redis_client.incrbyfloat(key, -cost)
                return False
            return True
        except Exception as e:
            logger.error(f"Redis cost hour limiting error, falling back to local: {e}")
            cls.is_fallback_active = True
            return LocalRateLimiterFallback.check_cost_hour(tenant_id, agent_id, cost, limit)

    @classmethod
    async def check_cost_run(
        cls, tenant_id: str, agent_id: str, run_id: str, cost: float, limit: float
    ) -> bool:
        """Rate limit: cost/run."""
        if cls._use_fallback():
            cls.is_fallback_active = True
            logger.info("Local rate limiter fallback activated for cost/run")
            return LocalRateLimiterFallback.check_cost_run(tenant_id, agent_id, run_id, cost, limit)

        cls.is_fallback_active = False
        key = f"rl:cost_run:{tenant_id}:{agent_id}:{run_id}"

        try:
            current = await redis_client.get(key)
            if current and float(current) + cost > limit:
                return False

            val = await redis_client.incrbyfloat(key, cost)
            await redis_client.expire(key, 86400)

            if val > limit:
                # Revert increment if exceeded
                await redis_client.incrbyfloat(key, -cost)
                return False
            return True
        except Exception as e:
            logger.error(f"Redis cost run limiting error, falling back to local: {e}")
            cls.is_fallback_active = True
            return LocalRateLimiterFallback.check_cost_run(tenant_id, agent_id, run_id, cost, limit)
