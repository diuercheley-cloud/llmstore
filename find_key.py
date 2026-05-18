import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import get_settings
from app.core.security import verify_secret

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT client_id, key_hash FROM api_keys"))
        rows = result.fetchall()
        for client_id, key_hash in rows:
            if verify_secret("TEST_API_KEY", key_hash):
                print(f"FOUND: {client_id}")
                return
        print("NOT FOUND")

if __name__ == '__main__':
    asyncio.run(main())