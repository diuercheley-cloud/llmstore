import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def list_clients():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT name, allowed_models_json FROM clients"))
        clients = result.fetchall()
        print("Name | Allowed Models")
        print("-" * 50)
        for c in clients:
            print(f"{c.name} | {c.allowed_models_json}")

if __name__ == "__main__":
    asyncio.run(list_clients())
