import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def delete_model():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        await session.execute(text("DELETE FROM model_backend_routes WHERE model_registry_id IN (SELECT id FROM model_registry WHERE model_alias = 'nemotron-3-nano-omni-30b-a3b-reasoning')"))
        await session.execute(text("DELETE FROM model_registry WHERE model_alias = 'nemotron-3-nano-omni-30b-a3b-reasoning'"))
        await session.commit()
        print("Model deleted")

if __name__ == "__main__":
    asyncio.run(delete_model())
