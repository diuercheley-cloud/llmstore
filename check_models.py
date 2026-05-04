import asyncio
from app.db.session import SessionLocal
from app.models.model_registry import ModelRegistry
from sqlalchemy import select

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(ModelRegistry))
        models = result.scalars().all()
        for m in models:
            print(f"ID: {m.model_id}, Alias: {m.model_alias}, Active: {m.is_active}")

if __name__ == "__main__":
    asyncio.run(main())
