# Graph Reasoning in the Knowledge Graph

> Owner: agent-platform | Status: beta

## Overview

The Knowledge Graph supports multi-hop **graph reasoning** — the ability for agents to traverse the entity-relation network and derive facts that are not explicitly stored as a single record.

Reasoning is powered by a BFS (Breadth-First Search) engine built into `InternalSQLGraphProvider` that operates entirely over the existing `agent_kg_entities` / `agent_kg_relations` SQL tables.

---

## Architecture

```
Agent
  │
  ▼
GraphReasoner / GraphRetriever
  │
  ▼
GraphStore (dispatcher)
  │
  ├─ entity_search  ──► InternalSQLGraphProvider.list_entities()
  ├─ neighborhood   ──► InternalSQLGraphProvider.related_entities()
  ├─ dependencies   ──► InternalSQLGraphProvider.dependency_traversal()   ← directed BFS
  └─ path           ──► InternalSQLGraphProvider.shortest_path()           ← BFS
```

---

## Query Types

| `query_type`   | Description |
|----------------|-------------|
| `entity_search` | Full-text ILIKE search over entity names |
| `neighborhood`  | 1-hop undirected neighbour set |
| `dependencies`  | Directed BFS following outgoing edges (dependency chain) |
| `path`          | BFS shortest path between two entities |

---

## PathResult Schema

Every pathfinding query returns a `PathResult`:

```python
class PathResult(BaseModel):
    status: PathStatus          # found | no_path | timeout | capability_not_supported | mock
    nodes: list[Entity]         # entities on the path (in order)
    edges: list[Relation]       # relations traversed (in order)
    relation_types: list[str]   # distinct relation types encountered
    provenance: list[dict]      # per-node source / document references
    confidence: float           # min confidence across all edges
    traversal_cost: int         # total edges examined during search
    query_time_ms: float        # wall-clock search time
    depth: int                  # hops in the result path
    reason: str                 # human-readable explanation when status != found
```

---

## PathStatus Values

| Status | Meaning |
|--------|---------|
| `found` | A path was found; `nodes` and `edges` are populated |
| `no_path` | No route exists between source and target |
| `timeout` | Search aborted after `timeout_ms` milliseconds |
| `capability_not_supported` | Provider does not implement pathfinding |
| `mock` | Mock mode active (`AGENT_KG_MOCK_MODE=true`) — test/staging only |

> [!IMPORTANT]
> An **empty `nodes` list** ONLY occurs when `status != found`.
> It is NEVER returned silently as a "not implemented" placeholder.

---

## Tenant Isolation

All graph queries include `tenant_id` in every SQL `WHERE` clause.
Cross-tenant node access is architecturally impossible:

- Entity UUIDs from tenant B will never appear in a tenant-A-scoped adjacency query.
- `GraphPolicy.validate_tenant()` is called at the `GraphStore.query()` boundary.
- `GraphPolicy.validate_tenant()` raises `PermissionError` on cross-tenant access.

---

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_KG_MOCK_MODE` | `false` | Allow mock path returns. **Never enable in production.** |
| `AGENT_KG_PATHFINDING_MAX_DEPTH` | `6` | Global default BFS depth limit |
| `AGENT_KG_PATHFINDING_MAX_NODES` | `500` | Global default node budget |
| `AGENT_KG_PATHFINDING_TIMEOUT_MS` | `5000` | Global default timeout |
| `AGENT_KG_ADJACENCY_CACHE_ENABLED` | `false` | LRU adjacency cache |
| `AGENT_KG_WRITE_ENABLED` | `false` | Allow entity/relation writes |

---

## GraphRAG Integration

`GraphRAG.query_with_path()` combines entity search with pathfinding to produce a citation-ready context block for LLM prompt injection:

```python
rag = GraphRAG(db)
result = await rag.query_with_path(
    tenant_id="acme",
    text="How does ServiceA depend on ServiceC?",
    source_entity_id=service_a_id,
    target_entity_id=service_c_id,
)
# result.context_block:
#   Vector Result: How does ServiceA depend on ServiceC?
#   Graph Result: ServiceA, ServiceB, ServiceC
#   Provenance: <source_id>
#   Path (2 hops, cost=3, confidence=1.00, time=4.2ms): ServiceA → ServiceB → ServiceC [depends_on]
#   Path Provenance: <entity_id>=<source_id>; ...
```

When no path exists the context block explains why:
```
Path not available: status=no_path
```

---

## Provider Capability Matrix

| Provider | Pathfinding | Algorithm |
|----------|------------|-----------|
| `internal_sql` | ✅ | Python BFS over SQL |
| `postgres` (pgrouting off) | ✅ | Inherits internal_sql |
| `postgres` (pgrouting on) | ✅ | pgr_dijkstra + fallback |
| `neo4j` | ❌ | Returns `capability_not_supported` |
| `falkordb` | ❌ | Returns `capability_not_supported` |

> [!NOTE]
> External providers (Neo4j, FalkorDB) return `PathStatus.capability_not_supported`
> rather than a silent empty list. This makes it explicit that pathfinding is unavailable.
