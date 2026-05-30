import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.vectorstores.vectorstore_factory import VectorStoreFactory
from app.services.vectorstores.pgvector_store import PGVectorStore
from app.services.vectorstores.qdrant_store import QdrantStore
from app.services.vectorstores.milvus_store import MilvusStore
from app.services.vectorstores.weaviate_store import WeaviateStore
from app.core.config import get_settings

settings = get_settings()

@pytest.mark.asyncio
async def test_factory_chooses_correct_provider():
    session = AsyncMock()
    
    # Test pgvector
    store = VectorStoreFactory.get_instance("pgvector", session=session)
    assert isinstance(store, PGVectorStore)
    
    # Test qdrant
    store = VectorStoreFactory.get_instance("qdrant")
    assert isinstance(store, QdrantStore)
    
    # Test milvus
    store = VectorStoreFactory.get_instance("milvus")
    assert isinstance(store, MilvusStore)
    
    # Test weaviate
    store = VectorStoreFactory.get_instance("weaviate")
    assert isinstance(store, WeaviateStore)

@pytest.mark.asyncio
async def test_qdrant_disabled_healthcheck():
    mock_settings = MagicMock()
    mock_settings.qdrant_enabled = False
    with patch("app.services.vectorstores.qdrant_store.settings", mock_settings):
        store = QdrantStore()
        health = await store.healthcheck()
        assert health["status"] == "disabled"
        assert health["provider"] == "qdrant"

@pytest.mark.asyncio
async def test_pgvector_healthcheck_mock():
    session = AsyncMock()
    # Mock extension check
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    session.execute.return_value = mock_result
    
    store = PGVectorStore(session)
    health = await store.healthcheck()
    assert health["status"] == "healthy"
    assert health["provider"] == "pgvector"

@pytest.mark.asyncio
async def test_delete_propagation_calls_provider():
    session = AsyncMock()
    store = PGVectorStore(session)
    
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    await store.delete("test_collection", ids)
    
    # Verify SQL execution
    assert session.execute.called
    call_args = session.execute.call_args
    assert "DELETE FROM rag_document_chunks" in str(call_args[0][0])

@pytest.mark.asyncio
async def test_tenant_isolation_param_passing():
    # Test if search passes filters which include client_id for isolation
    session = AsyncMock()
    store = PGVectorStore(session)
    
    client_id = str(uuid.uuid4())
    vector = [0.1] * 384
    
    await store.search(
        collection_name="test",
        vector=vector,
        filters={"client_id": client_id}
    )
    
    assert session.execute.called
    params = session.execute.call_args[0][1]
    assert params["client_id"] == client_id
