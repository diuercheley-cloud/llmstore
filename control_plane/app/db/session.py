from collections.abc import AsyncGenerator

from app.core.config import get_settings
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


from app.services.chaos.injection import inject_chaos, inject_chaos_db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    await inject_chaos_db()
    async with SessionLocal() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    await inject_chaos_db()
    async with SessionLocal() as session:
        yield session


async def get_redis() -> Redis:
    await inject_chaos("redis_failure")
    return redis_client
