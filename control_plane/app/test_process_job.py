import asyncio
import uuid
from app.db.session import SessionLocal, redis_client
from app.services.generation_jobs import process_generation_job
from app.api.deps import get_inference_proxy, get_backend_slot_manager

async def main():
    job_id = uuid.UUID("e83ae088-4c31-4804-9722-3a4b553f7509")
    async with SessionLocal() as session:
        print(f"Processing job {job_id}...")
        result = await process_generation_job(session, job_id, get_inference_proxy(), get_backend_slot_manager())
        print(f"Result: {result}")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
