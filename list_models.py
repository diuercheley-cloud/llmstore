import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
import sys

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def list_models():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        result = await session.execute(text("""
            SELECT m.model_id, m.model_alias, m.is_active, m.is_default, m.provider, m.inference_backend_id
            FROM model_registry m
        """))
        models = result.fetchall()
        print("Model ID | Alias | Active | Default | Provider | Backend ID")
        print("-" * 100)
        for m in models:
            print(f"{m.model_id} | {m.model_alias} | {m.is_active} | {m.is_default} | {m.provider} | {m.inference_backend_id}")

if __name__ == "__main__":
    asyncio.run(list_models())
