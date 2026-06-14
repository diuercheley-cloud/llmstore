from collections.abc import AsyncGenerator

from app.db.session import SessionLocal, get_db as _get_db, get_db_session as _get_db_session, get_redis as _get_redis, redis_client
from app.services.cache.semantic_cache_redis import get_semantic_cache as _get_semantic_cache
from app.services.inference_proxy import get_inference_proxy
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db_session():
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        yield session


async def get_redis() -> Redis:
    return await _get_redis()


def get_semantic_cache(redis: Redis):
    return _get_semantic_cache(redis)

