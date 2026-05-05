import asyncio
import logging
import uuid

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, redis_client
from app.services.rag_processor import process_rag_document

configure_logging()
logger = logging.getLogger(__name__)

RAG_QUEUE_NAME = "rag_jobs:queue"

async def _run_once() -> None:
    settings = get_settings()
    item = await redis_client.blpop(RAG_QUEUE_NAME, timeout=settings.async_worker_block_seconds)
    if item is None:
        return
    _, raw_doc_id = item
    try:
        doc_id = uuid.UUID(raw_doc_id)
    except ValueError:
        logger.warning(f"discarding invalid doc id from redis queue: {raw_doc_id}")
        return
    
    async with SessionLocal() as session:
        await process_rag_document(session, doc_id)

async def main() -> None:
    logger.info("RAG Worker started")
    while True:
        try:
            await _run_once()
        except Exception as e:
            logger.error(f"RAG Worker error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
