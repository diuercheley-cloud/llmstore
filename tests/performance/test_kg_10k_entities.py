import time
import uuid
import pytest
from pathlib import Path
from app.services.agents.knowledge_graph.graph_store import GraphStore
from app.services.agents.knowledge_graph.graph_models import GraphQueryRequest
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_kg_10k_entities_performance(session):
    settings = get_settings()
    settings.agent_kg_write_enabled = True
    settings.agent_knowledge_graph_enabled = True
    
    store = GraphStore(session)
    tenant_id = "perf-tenant"
    
    # Measure 10,000 insertions
    start_time = time.time()
    entity_ids = []
    
    # Let's batch/loop to insert entities
    for i in range(10000):
        # We can add entity directly to the session in bulk or through store.add_entity.
        # Since add_entity does a commit/refresh, bulk adding through store is slower.
        # Let's see if we can do bulk insertion or measure store.add_entity.
        # Let's insert in batches of 1000 to keep it fast, but total 10000.
        ent = await store.add_entity(
            tenant_id=tenant_id,
            name=f"Entity-{i}",
            entity_type="asset"
        )
        if i % 100 == 0:
            entity_ids.append(ent.id)
            
    insert_duration = time.time() - start_time
    
    # Measure query speed
    query_start = time.time()
    res = await store.get_entities(tenant_id, entity_name="Entity-999")
    query_duration = time.time() - query_start
    
    # Let's write some relations
    rel_start = time.time()
    for i in range(len(entity_ids) - 1):
        await store.add_relation(
            tenant_id=tenant_id,
            src_id=entity_ids[i],
            tgt_id=entity_ids[i+1],
            relation_type="depends_on",
            provenance="perf-test"
        )
    rel_duration = time.time() - rel_start
    
    # Create artifacts directory and write report
    report_dir = Path("artifacts/benchmarks")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "kg-10k-summary.md"
    
    report_content = f"""# Knowledge Graph 10k Entities Benchmark Summary

- **Total Entities Inserted**: 10,000
- **Total Relations Inserted**: {len(entity_ids) - 1}
- **Entity Insertion Duration**: {insert_duration:.4f} seconds (avg {(insert_duration/10000)*1000:.4f} ms/entity)
- **Relation Insertion Duration**: {rel_duration:.4f} seconds
- **Entity Query Latency**: {query_duration*1000:.4f} ms
- **Database Backend**: SQLite (internal_sql)
"""
    report_path.write_text(report_content)
    assert len(res) >= 1
