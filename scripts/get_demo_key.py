import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def get_key():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT k.api_key FROM api_keys k JOIN clients c ON k.client_id = c.id WHERE c.name = 'demo-client' LIMIT 1"))
        key = result.scalar()
        print(key)

if __name__ == "__main__":
    asyncio.run(get_key())
