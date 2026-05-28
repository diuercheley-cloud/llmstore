import pytest
import uuid
from app.services.agents.knowledge_graph.graph_store import GraphStore
from app.services.agents.knowledge_graph.graph_models import Relation, GraphQueryRequest
from app.services.agents.knowledge_graph.graph_policy import graph_policy
from app.services.agents.knowledge_graph.graph_rag import GraphRAG
from app.services.agents.knowledge_graph.providers.neo4j_graph import Neo4jGraphProvider
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_internal_sql_graph_persists_entities(session):
    settings = get_settings()
    settings.agent_kg_write_enabled = True
    
    store = GraphStore(session)
    entity = await store.add_entity(
        tenant_id="tenant-a",
        name="Project Phoenix",
        entity_type="project"
    )
    assert entity.id is not None
    assert entity.name == "Project Phoenix"
    assert entity.type == "project"
    
    entities = await store.get_entities("tenant-a")
    assert len(entities) == 1
    assert entities[0].name == "Project Phoenix"

@pytest.mark.asyncio
async def test_relation_without_provenance_fails(session):
    relation = Relation(
        id=str(uuid.uuid4()),
        tenant_id="tenant-a",
        source_entity_id=str(uuid.uuid4()),
        target_entity_id=str(uuid.uuid4()),
        type="depends_on",
        provenance=""
    )
    with pytest.raises(ValueError, match="Provenance is required"):
        graph_policy.check_provenance(relation)

@pytest.mark.asyncio
async def test_cross_tenant_access_blocked(session):
    store = GraphStore(session)
    with pytest.raises(PermissionError, match="Cross-tenant graph access is blocked"):
        graph_policy.validate_tenant("tenant-a", "tenant-b")

@pytest.mark.asyncio
async def test_graph_rag_returns_provenance(session):
    settings = get_settings()
    settings.agent_kg_write_enabled = True
    
    store = GraphStore(session)
    source_id = await store.create_source("tenant-a", "http://test-doc", "Google owns Android")
    
    # Google is organizations, Android is documents/systems
    entity_a = await store.add_entity("tenant-a", "Google", "organization", source_id=source_id)
    entity_b = await store.add_entity("tenant-a", "Android", "system", source_id=source_id)
    
    await store.add_relation(
        tenant_id="tenant-a",
        src_id=entity_a.id,
        tgt_id=entity_b.id,
        relation_type="owns",
        provenance="Google owns Android",
        source_id=source_id
    )
    
    rag = GraphRAG(session)
    res = await rag.query("tenant-a", "Google")
    assert len(res.entities) > 0
    assert "Google" in res.context_block
    assert str(source_id) in res.context_block

@pytest.mark.asyncio
async def test_kg_write_disabled_blocks_mutation(session):
    settings = get_settings()
    settings.agent_kg_write_enabled = False
    
    store = GraphStore(session)
    with pytest.raises(PermissionError, match="Knowledge graph write path is disabled"):
        await store.add_entity("tenant-a", "Google", "organization")

def test_neo4j_provider_fails_if_disabled():
    with pytest.raises(RuntimeError, match="Neo4j graph provider is disabled"):
        Neo4jGraphProvider(enabled=False)

def test_secret_redacted_before_persistence():
    text_with_secret = "Google api_key='sk-1234567890abcdef' depends on Android"
    redacted = graph_policy.redact_secrets(text_with_secret)
    assert "sk-1234567890abcdef" not in redacted
    assert "api_key=[REDACTED]" in redacted
