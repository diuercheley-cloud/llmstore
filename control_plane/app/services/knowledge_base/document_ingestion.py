# Owner: agent-platform
import hashlib
import logging
import uuid

from app.core.time import utc_now
from app.models.rag.knowledge_base import KBChunk, KBIngestionJob
from app.services.knowledge_base.chunker import KBChunker
from app.services.knowledge_base.kb_registry import KBRegistry
from app.services.knowledge_base.pdf_ingestor import PDFIngestor
from app.services.knowledge_base.web_ingestor import WebIngestor
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Orchestrates the end-to-end ingestion process for KB documents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = KBRegistry(db)
        self.chunker = KBChunker()
        self.pdf_ingestor = PDFIngestor()
        self.web_ingestor = WebIngestor()

    async def ingest_file(self, kb_id: uuid.UUID, name: str, content: bytes) -> KBIngestionJob:
        """
        Processes an uploaded file.
        """
        job = await self._create_job(kb_id)

        try:
            # 1. Register doc
            doc = await self.registry.register_document(kb_id, name, "file")

            # 2. Extract text (assuming PDF for now)
            extracted = await self.pdf_ingestor.ingest(content)
            text = extracted["text"]

            # 3. Create version
            content_hash = hashlib.sha256(content).hexdigest()
            version = await self.registry.create_document_version(doc.id, "v1", content_hash)

            # 4. Chunk and store
            chunks = self.chunker.split_document(text, extracted["metadata"])
            for c in chunks:
                chunk_obj = KBChunk(
                    version_id=version.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    metadata_json=c["metadata"],
                )
                self.db.add(chunk_obj)

            await self._complete_job(job)
        except Exception as e:
            await self._fail_job(job, str(e))
            raise e

        await self.db.commit()
        return job

    async def ingest_url(self, kb_id: uuid.UUID, url: str) -> KBIngestionJob:
        """
        Processes a web URL.
        """
        job = await self._create_job(kb_id)

        try:
            # 1. Register doc
            name = url.split("/")[-1] or "web_doc"
            doc = await self.registry.register_document(kb_id, name, "url", source_url=url)

            # 2. Scrape
            extracted = await self.web_ingestor.ingest(url)
            text = extracted["text"]

            # 3. Create version
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            version = await self.registry.create_document_version(doc.id, "v1", content_hash)

            # 4. Chunk and store
            chunks = self.chunker.split_document(text, extracted["metadata"])
            for c in chunks:
                chunk_obj = KBChunk(
                    version_id=version.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    metadata_json=c["metadata"],
                )
                self.db.add(chunk_obj)

            await self._complete_job(job)
        except Exception as e:
            await self._fail_job(job, str(e))
            raise e

        await self.db.commit()
        return job

    async def _create_job(self, kb_id: uuid.UUID) -> KBIngestionJob:
        kb = await self.registry.get_kb(kb_id)
        job = KBIngestionJob(kb_id=kb_id, tenant_id=kb.tenant_id, status="running")
        self.db.add(job)
        await self.db.flush()
        return job

    async def _complete_job(self, job: KBIngestionJob):
        job.status = "completed"
        job.progress = 1.0
        job.completed_at = utc_now()

    async def _fail_job(self, job: KBIngestionJob, error: str):
        job.status = "failed"
        job.error_message = error
        job.completed_at = utc_now()
