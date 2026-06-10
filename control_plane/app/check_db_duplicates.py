import asyncio

from app.db.session import SessionLocal
from app.models.core.model_registry import ModelRegistry
from sqlalchemy import func, select


async def main():
    async with SessionLocal() as session:
        # Check for duplicate aliases
        result = await session.execute(
            select(ModelRegistry.model_alias, func.count(ModelRegistry.id))
            .group_by(ModelRegistry.model_alias)
            .having(func.count(ModelRegistry.id) > 1)
        )
        duplicates = result.all()
        if duplicates:
            print(f"Found duplicate aliases: {duplicates}")
        else:
            print("No duplicate aliases found.")
        
        # List all models
        result = await session.execute(select(ModelRegistry))
        models = result.scalars().all()
        for m in models:
            print(f"Model ID: {m.model_id}, Alias: {m.model_alias}, ID: {m.id}")

if __name__ == "__main__":
    asyncio.run(main())
