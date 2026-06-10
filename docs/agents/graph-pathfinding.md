# Graph Pathfinding

> Owner: agent-platform | Status: beta

## Overview

The Knowledge Graph provides **three pathfinding algorithms** available through the `InternalSQLGraphProvider` (and `PostgresGraphProvider` which inherits from it):

| Algorithm | Method | Direction | Use case |
|-----------|--------|-----------|----------|
| BFS Shortest Path | `shortest_path()` | Undirected | Find the shortest connection between two entities |
| Bounded BFS | `bounded_bfs()` | Undirected or Directed | Explore a subgraph up to N hops |
| Dependency Traversal | `dependency_traversal()` | Directed (outgoing) | Follow dependency chains |

---

## BFS Shortest Path

### Algorithm

Standard iterative BFS with **frontier batching**: all nodes in the current frontier are queried in a single `SELECT ... WHERE id IN (...)` statement per hop. This minimises round-trips to the database.

```
hop 0: frontier = {source}
hop 1: SELECT relations WHERE source_entity_id IN frontier OR target_entity_id IN frontier
         → expand frontier to new neighbours
hop 2: repeat until target found or max_depth reached
```

Path reconstruction walks the `parent_edge` map from target back to source in O(path_length).

### Complexity

| Bound | Worst case |
|-------|-----------|
| SQL queries | `max_depth` (one per hop) |
| Nodes examined | `min(max_nodes, total_reachable)` |
| Wall time | `timeout_ms` |

### Tenant Isolation

Every SQL query includes `WHERE tenant_id = :tid`.
The BFS engine cannot traverse edges from a different tenant because
the adjacency queries are scoped to a single tenant.

---

## Parameters

All pathfinding methods accept the following bounds:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_depth` | int | 6 | Maximum BFS hops |
| `max_nodes` | int | 500 | Maximum nodes visited before aborting |
| `timeout_ms` | int | 5000 | Wall-clock timeout in milliseconds |
| `relation_types` | list[str] \| None | None | Restrict traversal to these relation types |
| `directed` | bool | False | If True, only follow outgoing edges |

Per-query overrides take precedence over global defaults set in environment variables.

---

## API Usage

### Via GraphRetriever (recommended)

```python
from app.services.agents.knowledge_graph.graph_retriever import GraphRetriever

retriever = GraphRetriever(db)

# Shortest path
path = await retriever.find_path(
    tenant_id="acme",
    source_entity_id=str(service_a_id),
    target_entity_id=str(service_c_id),
    relation_type="depends_on",   # optional filter
    max_depth=4,
    timeout_ms=3000,
)
print(path.status)           # PathStatus.found
print(path.depth)            # 2
print(path.traversal_cost)   # edges examined
print(path.query_time_ms)    # wall clock

# Dependency traversal
deps = await retriever.get_dependencies(
    tenant_id="acme",
    entity_id=str(service_a_id),
    max_depth=3,
)
```

### Via GraphStore (lower level)

```python
from app.services.agents.knowledge_graph.graph_store import GraphStore
from app.services.agents.knowledge_graph.graph_models import GraphQueryRequest

store = GraphStore(db)
result = await store.query(GraphQueryRequest(
    tenant_id="acme",
    query_type="path",
    entity_id=str(service_a_id),
    target_entity_id=str(service_c_id),
    max_depth=6,
    max_nodes=500,
    timeout_ms=5000,
))
path = result.path
```

### Via GraphReasoner (agent interface)

```python
from app.services.agents.knowledge_graph.graph_reasoner import GraphReasoner

reasoner = GraphReasoner(db)
path = await reasoner.find_path(
    tenant_id="acme",
    src_id=str(entity_a_id),
    dst_id=str(entity_b_id),
)
```

---

## PathResult Fields

```python
PathResult(
    status=PathStatus.found,
    nodes=[Entity(name="A"), Entity(name="B"), Entity(name="C")],
    edges=[Relation(type="depends_on"), Relation(type="depends_on")],
    relation_types=["depends_on"],
    provenance=[
        {"entity_id": "...", "source_id": "...", "provenance": {...}},
        ...
    ],
    confidence=0.95,       # min confidence across edges
    traversal_cost=7,      # edges examined
    query_time_ms=12.3,
    depth=2,
    reason="",             # empty when status==found
)
```

---

## Status Semantics

| `status` | `nodes` | `edges` | `reason` |
|----------|---------|---------|---------|
| `found` | populated | populated | `""` |
| `no_path` | `[]` | `[]` | `"status=no_path"` |
| `timeout` | `[]` | `[]` | `"status=timeout"` |
| `capability_not_supported` | `[]` | `[]` | explains provider limitation |
| `mock` | `[]` | `[]` | `"AGENT_KG_MOCK_MODE=true – real pathfinding disabled"` |

> [!IMPORTANT]
> An empty `nodes` list is **never returned silently** as a "not implemented" placeholder.
> Every empty result carries a machine-readable `status` and human-readable `reason`.

---

## Relation Filtering

Pass `relation_type` to restrict BFS to a single edge type:

```python
# Only traverse "depends_on" edges
path = await retriever.find_path(
    tenant_id="acme",
    source_entity_id=a_id,
    target_entity_id=b_id,
    relation_type="depends_on",
)
```

If the path exists only via a different relation type, `status=no_path` is returned.

---

## Mock Mode

> [!CAUTION]
> `AGENT_KG_MOCK_MODE=true` allows providers to return `PathStatus.mock` with an
> empty path.  **This must never be enabled in production.**
> Production environments must use real pathfinding or get `no_path` / `capability_not_supported`.

In test/staging environments:
```shell
AGENT_KG_MOCK_MODE=true
```

The returned PathResult will have `status=mock` and `reason` will explain that mock mode is active,
making it impossible to confuse mock behaviour with a genuine empty graph.

---

## PostgreSQL pgrouting (optional)

When `AGENT_KG_PGROUTING_ENABLED=true`, `PostgresGraphProvider.shortest_path()` uses
`pgr_dijkstra` for database-native shortest-path computation, falling back to the Python
BFS if the extension is unavailable or raises an error.

```shell
AGENT_KG_POSTGRES_GRAPH_ENABLED=true
AGENT_KG_PGROUTING_ENABLED=true
```

The result schema is identical to the Python BFS path — callers do not need to handle both paths.

---

## Testing

Run pathfinding tests with:

```shell
pytest tests/unit/services/test_knowledge_graph.py -v -k "path"
```

Key test cases:

| Test | Description |
|------|-------------|
| `test_path_direct_ab` | Direct A→B path found |
| `test_path_indirect_a_to_c_via_b` | A→C via B (2 hops) |
| `test_path_max_depth_blocks_long_path` | max_depth=1 cannot reach C |
| `test_path_relation_filter` | Wrong relation type returns no_path |
| `test_path_tenant_isolation` | No cross-tenant nodes in path |
| `test_path_no_path_returns_empty_with_reason` | Isolated nodes → no_path |
| `test_path_external_provider_returns_capability_not_supported` | Mock provider → capability_not_supported |
| `test_graphrag_query_with_path_injects_provenance` | GraphRAG context_block with citations |
| `test_mock_mode_returns_mock_status` | AGENT_KG_MOCK_MODE=true → mock status |
