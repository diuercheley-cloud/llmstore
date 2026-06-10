# Owner: agent-platform
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.rag.knowledge_base import KBDocument, KBDocumentVersion, KnowledgeBase
from app.services.knowledge_base.chunker import KBChunker
from app.services.knowledge_base.document_ingestion import DocumentIngestionService
from app.services.knowledge_base.kb_registry import KBRegistry
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_kb_registry_create(mock_db):
    registry = KBRegistry(mock_db)
    kb = await registry.create_kb("tenant_1", "My KB")
    
    assert kb.name == "My KB"
    assert kb.tenant_id == "tenant_1"

def test_chunking_logic():
    chunker = KBChunker(chunk_size=10, chunk_overlap=2)
    text = "abcdefghij0123456789" # 20 chars
    
    chunks = chunker.split_text(text)
    # 0: abcdefghij (len 10)
    # 1: ij01234567 (start 8, len 10)
    # ...
    assert len(chunks) > 1
    assert chunks[0] == "abcdefghij"
    assert chunks[1].startswith("ij")

@pytest.mark.asyncio
async def test_ingest_url_disabled_by_default(mock_db):
    service = DocumentIngestionService(mock_db)
    kb_id = uuid.uuid4()
    
    # Mock KB retrieval
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: KnowledgeBase(id=kb_id, tenant_id="t1")))
    
    # URL ingestion should fail by default
    with pytest.raises(PermissionError, match="URL ingestion is disabled"):
        await service.ingest_url(kb_id, "https://example.com")

@pytest.mark.asyncio
async def test_ingest_file_success(mock_db):
    service = DocumentIngestionService(mock_db)
    kb_id = uuid.uuid4()
    
    # Mock KB and Registry
    service.registry.get_kb = AsyncMock(return_value=KnowledgeBase(id=kb_id, tenant_id="t1"))
    service.registry.register_document = AsyncMock(return_value=KBDocument(id=uuid.uuid4()))
    service.registry.create_document_version = AsyncMock(return_value=KBDocumentVersion(id=uuid.uuid4()))
    
    # Mock PDF extraction
    service.pdf_ingestor.ingest = AsyncMock(return_value={"text": "Hello world", "metadata": {}})
    
    job = await service.ingest_file(kb_id, "test.pdf", b"pdf_content")
    
    assert job.status == "completed"
    assert job.progress == 1.0
