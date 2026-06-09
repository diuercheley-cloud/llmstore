import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.append(os.path.join(os.getcwd(), "control_plane"))

async def list_routes():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    async with AsyncSession(engine) as session:
        result = await session.execute(text("""
            SELECT r.id, m.model_id, b.name as backend_name, r.priority, r.weight, r.state
            FROM model_backend_routes r
            JOIN model_registry m ON r.model_registry_id = m.id
            JOIN inference_backends b ON r.inference_backend_id = b.id
        """))
        routes = result.fetchall()
        print("ID | Model ID | Backend | Priority | Weight | State")
        print("-" * 100)
        for r in routes:
            print(f"{r.id} | {r.model_id} | {r.backend_name} | {r.priority} | {r.weight} | {r.state}")

if __name__ == "__main__":
    asyncio.run(list_routes())
