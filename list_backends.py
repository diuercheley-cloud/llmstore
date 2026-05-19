import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def list_backends():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT id, name, provider, is_active FROM inference_backends"))
        backends = result.fetchall()
        print("ID | Name | Provider | Active")
        print("-" * 50)
        for b in backends:
            print(f"{b.id} | {b.name} | {b.provider} | {b.is_active}")

if __name__ == "__main__":
    asyncio.run(list_backends())
