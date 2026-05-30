import pytest
import uuid
from datetime import datetime, timedelta, timezone
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentMemoryItem
from app.services.agents.memory.semantic_memory_retriever import SemanticMemoryRetriever, _MOCK_STORE
from app.services.agents.memory.mock_memory_store import MockMemoryStore

@pytest.fixture(autouse=True)
def clear_mock_store():
    _MOCK_STORE.clear()

@pytest.mark.asyncio
async def test_mock_store_persistence(session):
    # Verify the singleton _MOCK_STORE actually persists within a test
    settings = get_settings()
    settings.agent_semantic_memory_enabled = True
    settings.agent_memory_vector_provider = "mock"
    
    retriever = SemanticMemoryRetriever(session)
    tenant_id = "tenant-p"
    agent_id = uuid.uuid4()
    
    item = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        raw_content="Persistent content",
        content_hash="hash-p",
        retention_until=utc_now() + timedelta(days=1),
        memory_type="long_term"
    )
    session.add(item)
    await session.commit()
    
    await retriever.index_memory(tenant_id, agent_id, item)
    
    # New retriever instance should see the same mock store
    retriever2 = SemanticMemoryRetriever(session)
    results = await retriever2.retrieve_semantic(tenant_id, agent_id, "Persistent")
    assert len(results) == 1

@pytest.mark.asyncio
async def test_semantic_retrieval_flow(session):
    settings = get_settings()
    settings.agent_semantic_memory_enabled = True
    settings.agent_memory_vector_provider = "mock"
    
    retriever = SemanticMemoryRetriever(session)
    tenant_id = "tenant-1"
    agent_id = uuid.uuid4()
    
    # 1. Create a memory item
    item = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        raw_content="Python is a high-level, general-purpose programming language.",
        content_hash="hash1",
        retention_until=utc_now() + timedelta(days=1),
        summary="About Python",
        memory_type="long_term"
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    # 2. Index it
    await retriever.index_memory(tenant_id, agent_id, item)
    
    # 3. Retrieve it
    results = await retriever.retrieve_semantic(tenant_id, agent_id, "What is Python?", top_k=1)
    
    assert len(results) == 1
    assert "Python" in results[0]["content"]
    assert results[0]["provider"] == "mock"

@pytest.mark.asyncio
async def test_tenant_isolation(session):
    settings = get_settings()
    settings.agent_semantic_memory_enabled = True
    settings.agent_memory_vector_provider = "mock"
    
    retriever = SemanticMemoryRetriever(session)
    agent_id = uuid.uuid4()
    
    # Item for tenant 1
    item1 = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id="tenant-1",
        agent_id=agent_id,
        raw_content="Content for tenant one secret",
        content_hash="hash2",
        retention_until=utc_now() + timedelta(days=1),
        memory_type="long_term"
    )
    # Item for tenant 2
    item2 = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id="tenant-2",
        agent_id=agent_id,
        raw_content="Content for tenant two secret",
        content_hash="hash3",
        retention_until=utc_now() + timedelta(days=1),
        memory_type="long_term"
    )
    session.add_all([item1, item2])
    await session.commit()
    
    await retriever.index_memory("tenant-1", agent_id, item1)
    await retriever.index_memory("tenant-2", agent_id, item2)
    
    # Search as tenant 1
    results1 = await retriever.retrieve_semantic("tenant-1", agent_id, "tenant one secret")
    assert len(results1) == 1
    assert "one" in results1[0]["content"]
    
    # Search as tenant 2
    results2 = await retriever.retrieve_semantic("tenant-2", agent_id, "tenant two secret")
    assert len(results2) == 1
    assert "two" in results2[0]["content"]

@pytest.mark.asyncio
async def test_score_threshold(session):
    settings = get_settings()
    settings.agent_semantic_memory_enabled = True
    settings.agent_memory_vector_provider = "mock"
    
    retriever = SemanticMemoryRetriever(session)
    tenant_id = "tenant-1"
    agent_id = uuid.uuid4()
    
    item = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        raw_content="The weather is nice today.",
        content_hash="hash4",
        retention_until=utc_now() + timedelta(days=1),
        memory_type="long_term"
    )
    session.add(item)
    await session.commit()
    
    await retriever.index_memory(tenant_id, agent_id, item)
    
    # Query with low relevance
    results = await retriever.retrieve_semantic(tenant_id, agent_id, "Quantum physics", score_threshold=0.9)
    assert len(results) == 0

@pytest.mark.asyncio
async def test_memory_erasure_semantic(session):
    settings = get_settings()
    settings.agent_semantic_memory_enabled = True
    settings.agent_memory_vector_provider = "mock"
    
    retriever = SemanticMemoryRetriever(session)
    tenant_id = "tenant-1"
    agent_id = uuid.uuid4()
    
    item = AgentMemoryItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        raw_content="Forgettable info",
        content_hash="hash5",
        retention_until=utc_now() + timedelta(days=1),
        memory_type="long_term"
    )
    session.add(item)
    await session.commit()
    
    await retriever.index_memory(tenant_id, agent_id, item)
    
    # Delete from DB
    await session.delete(item)
    await session.commit()
    
    # Retriever should return empty because hydration fails
    results = await retriever.retrieve_semantic(tenant_id, agent_id, "Forgettable")
    assert len(results) == 0
