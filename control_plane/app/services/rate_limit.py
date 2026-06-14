import time
from uuid import UUID

from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    pass


async def enforce_rate_limit(redis: Redis, client_id: UUID, limit_per_minute: int) -> None:
    current_minute = int(time.time() // 60)
    key = f"ratelimit:client:{client_id}:{current_minute}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
    if current > limit_per_minute:
        raise RateLimitExceeded(f"client exceeded {limit_per_minute} requests per minute")


async def enforce_ip_rate_limit(redis: Redis, source_ip: str, limit_per_minute: int = 60) -> None:
    # Global IP rate limit to prevent brute force or massive distributed abuse
    current_minute = int(time.time() // 60)
    key = f"ratelimit:ip:{source_ip}:{current_minute}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
    if current > limit_per_minute:
        raise RateLimitExceeded(f"IP address {source_ip} exceeded {limit_per_minute} requests per minute")


async def enforce_global_rate_limit(redis: Redis, limit_per_minute: int = 1000) -> None:
    # Protects the whole SaaS cluster from massive spikes
    current_minute = int(time.time() // 60)
    key = f"ratelimit:global:{current_minute}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
    if current > limit_per_minute:
        raise RateLimitExceeded(f"Global rate limit exceeded ({limit_per_minute} req/min)")


async def enforce_tenant_rate_limit(redis: Redis, tenant_id: str, limit_per_minute: int = 500) -> None:
    current_minute = int(time.time() // 60)
    key = f"ratelimit:tenant:{tenant_id}:{current_minute}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
    if current > limit_per_minute:
        raise RateLimitExceeded(f"Tenant {tenant_id} rate limit exceeded ({limit_per_minute} req/min)")


async def enforce_client_rate_limit(redis: Redis, client_id: str, limit_per_minute: int = 1000) -> None:
    current_minute = int(time.time() // 60)
    key = f"ratelimit:client:{client_id}:{current_minute}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 65)
    if current > limit_per_minute:
        raise RateLimitExceeded(f"Client {client_id} exceeded {limit_per_minute} req/min")

