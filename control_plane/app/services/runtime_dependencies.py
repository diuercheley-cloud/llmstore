from collections.abc import AsyncGenerator

from app.db.session import (
    SessionLocal,  # noqa: F401
    redis_client,  # noqa: F401
)
from app.db.session import (
    get_db as _get_db,
)
from app.db.session import (
    get_db_session as _get_db_session,
)
from app.db.session import (
    get_redis as _get_redis,
)
from app.services.cache.semantic_cache_redis import get_semantic_cache as _get_semantic_cache
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
