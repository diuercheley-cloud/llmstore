import uuid

import pytest
from app.db.base import Base
from app.services.agents.knowledge_graph.graph_extractor import GraphExtractor
from app.services.agents.knowledge_graph.graph_models import Relation
from app.services.agents.knowledge_graph.graph_policy import GraphPolicy
from app.services.agents.knowledge_graph.graph_rag import GraphRAG
from app.services.agents.knowledge_graph.graph_store import GraphStore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def kg_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_extractor_creates_entity_and_relation():
    extractor = GraphExtractor()
    entities, relations = extractor.extract_entities_and_relations("Alice owns ProjectX", tenant_id="tenant-1")
    assert len(entities) > 0
    assert len(relations) > 0
    assert relations[0].type == "owns"


def test_relation_without_source_fails():
    policy = GraphPolicy()
    relation = Relation(
        id="1",
        tenant_id="tenant-1",
        source_entity_id=str(uuid.uuid4()),
        target_entity_id=str(uuid.uuid4()),
        type="owns",
        provenance="",
    )
    with pytest.raises(ValueError, match="Provenance is required"):
        policy.check_provenance(relation)


def test_tenant_cross_access_is_blocked():
    policy = GraphPolicy()
    with pytest.raises(PermissionError, match="Cross-tenant"):
        policy.validate_tenant("tenant-a", "tenant-b")


@pytest.mark.asyncio
async def test_internal_sql_graph_persists_entities(kg_db):
    store = GraphStore(kg_db)
    store.settings.agent_kg_write_enabled = True
    entity = await store.add_entity("tenant-1", "Alice", "person")
    entities = await store.get_entities("tenant-1", entity_name="Alice")
    assert any(item.id == entity.id for item in entities)


@pytest.mark.asyncio
async def test_graph_rag_returns_subgraph_with_provenance(kg_db):
    store = GraphStore(kg_db)
    store.settings.agent_kg_write_enabled = True
    alice = await store.add_entity("tenant-1", "Alice", "person")
    project = await store.add_entity("tenant-1", "ProjectX", "project")
    await store.add_relation("tenant-1", alice.id, project.id, "owns", "unit-test")
    result = await GraphRAG(kg_db).query("tenant-1", "Alice")
    assert "Graph Result" in result.context_block
    assert isinstance(result.provenance, list)


@pytest.mark.asyncio
async def test_kg_write_disabled_blocks_mutation(kg_db):
    store = GraphStore(kg_db)
    store.settings.agent_kg_write_enabled = False
    with pytest.raises(PermissionError, match="disabled"):
        await store.add_entity("tenant-1", "Alice", "person")


def test_secret_like_content_is_redacted():
    policy = GraphPolicy()
    redacted = policy.redact_secrets("api_key='super-secret' and AKIA123456789012")
    assert "super-secret" not in redacted
    assert "AKIA123456789012" not in redacted
