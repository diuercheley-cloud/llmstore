import asyncio
import os
import sys

# Add control_plane to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "control_plane")))

from app.db.session import SessionLocal
from app.services.runtime_tuning import RuntimeTuningService


async def main():
    async with SessionLocal() as db:
        service = RuntimeTuningService(db)
        await service.seed_default_profiles()
        print("Perfis semeados com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
