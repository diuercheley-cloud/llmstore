import asyncio

from app.core.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def test():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT model_id, provider FROM model_registry WHERE model_id LIKE '%nemotron%';"))
        print(result.fetchall())
        
        result = await session.execute(text("SELECT id, provider FROM inference_backends WHERE provider = 'openrouter'"))
        print(result.fetchall())

asyncio.run(test())
