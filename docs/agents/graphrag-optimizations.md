---
owner: platform-ops
status: consolidated
---

# GraphRAG Production Optimizations

> **Owner:** agent-platform  
> **Status:** experimental — all flags default `false`

## Overview

Four complementary production optimizations reduce query-latency degradation in dense Knowledge Graphs:

| Module | Feature flag | Purpose |
|--------|-------------|---------|
| `graph_cache.py` | `AGENT_KG_ADJACENCY_CACHE_ENABLED` | Per-tenant LRU cache; TTL + invalidation on write |
| `providers/postgres_graph.py` | `AGENT_KG_POSTGRES_GRAPH_ENABLED` | Postgres provider with SQL-layer fan-out limit |
| `graph_query_optimizer.py` | _(always active)_ | Depth/fan-out caps, hard timeout, explain plans |
| `vector_graph_hybrid.py` | composed of above flags | Vector + graph BFS combined retrieval |

---

## Feature Flags

```bash
# All default false — opt in per-environment
AGENT_KG_ADJACENCY_CACHE_ENABLED=false
AGENT_KG_POSTGRES_GRAPH_ENABLED=false
AGENT_KG_PGVECTOR_ENABLED=false
AGENT_KG_PGROUTING_ENABLED=false
```

---

## 1. Adjacency Cache (`graph_cache.py`)

### Design

```
AdjacencyCache (singleton)
  └── _TenantCache per tenant_id
        ├── LRU OrderedDict (max_size per tenant)
        ├── TTL-based expiry (per entry)
        └── hit/miss counters
```

- **Tenant isolation:** Each tenant has its own `_TenantCache`. Cross-tenant data sharing is impossible at the cache layer.
- **Write-through invalidation:** Every `GraphStore.add_entity()` and `add_relation()` call flushes the relevant tenant's cache entries immediately.
- **LRU eviction:** Oldest-unused entry is dropped when the cache exceeds `max_size`.
- **Metrics:** `adjacency_cache.metrics(tenant_id)` returns `hits`, `misses`, `hit_rate`, `size`.

### Configuration (future flags)

| Setting | Default | Meaning |
|---------|---------|---------|
| `AGENT_KG_ADJACENCY_CACHE_MAX_SIZE` | 5000 | Max entries per tenant |
| `AGENT_KG_ADJACENCY_CACHE_TTL_SECONDS` | 300 | Seconds before expiry |

### Usage

```python
from app.services.agents.knowledge_graph.graph_cache import adjacency_cache

# Manual warm-up (done automatically inside VectorGraphHybrid)
adjacency_cache.set(tenant_id, entity_id, (entities, relations))

# Invalidate on write (done automatically inside GraphStore)
adjacency_cache.invalidate(tenant_id)               # entire tenant
adjacency_cache.invalidate(tenant_id, entity_id)    # single entity

# Observability
print(adjacency_cache.metrics("my-tenant"))
# {'hits': 42, 'misses': 8, 'hit_rate': 0.84, 'size': 150}
```

---

## 2. PostgreSQL Graph Provider (`providers/postgres_graph.py`)

### Provider selection

`GraphStore._get_provider()` now resolves providers in this order:

1. `neo4j` — when `AGENT_KG_PROVIDER=neo4j`
2. `falkordb` — when `AGENT_KG_PROVIDER=falkordb`
3. `postgres` — when `AGENT_KG_PROVIDER=postgres` **or** `AGENT_KG_POSTGRES_GRAPH_ENABLED=true`
4. `internal_sql` — default fallback

### Fan-out limit at the SQL layer

`PostgresGraphProvider.related_entities()` applies `LIMIT max_fan_out` directly in the SQL query, preventing Python from materialising thousands of rows from dense neighbour sets before truncation.

### pgvector (optional)

When `AGENT_KG_PGVECTOR_ENABLED=true`, `vector_search()` executes:

```sql
SELECT id FROM agent_kg_entities
WHERE tenant_id = :tid AND embedding IS NOT NULL
ORDER BY embedding <=> CAST(:embedding AS vector)
LIMIT :top_k
```

> **Prerequisite:** `CREATE EXTENSION IF NOT EXISTS vector;` and an `embedding vector(N)` column on `agent_kg_entities`.

Falls back to ILIKE entity search when disabled.

### pgrouting (optional)

When `AGENT_KG_PGROUTING_ENABLED=true`, `shortest_path()` uses `pgr_dijkstra` on the relations table viewed as a weighted edge set. Falls back to BFS-approximation (`related_entities`) on any error.

> **Prerequisite:** `CREATE EXTENSION IF NOT EXISTS pgrouting;`

---

## 3. Query Optimizer (`graph_query_optimizer.py`)

Every graph query is validated and optionally explained before execution.

### Limits (configurable via settings)

| Setting | Default |
|---------|---------|
| `AGENT_KG_QUERY_MAX_DEPTH` | 3 |
| `AGENT_KG_QUERY_MAX_FAN_OUT` | 50 |
| `AGENT_KG_QUERY_TIMEOUT_SECONDS` | 10.0 |
| `AGENT_KG_QUERY_MAX_DEPTH_HARD_CAP` | 10 |
| `AGENT_KG_QUERY_MAX_FAN_OUT_HARD_CAP` | 200 |

### Explain plan

```python
from app.services.agents.knowledge_graph.graph_query_optimizer import (
    query_optimizer, OptimizedQueryRequest
)

plan = query_optimizer.build_plan(OptimizedQueryRequest(
    tenant_id="my-tenant",
    query_type="neighborhood",
    entity_id="...",
    max_depth=4,
    max_fan_out=100,
    limit=10,
))
print(plan.to_dict())
# {'query_type': 'neighborhood', 'warnings': ['Estimated 100,000,000 nodes …'], ...}
```

### Timeout

```python
result = await query_optimizer.run_with_timeout(my_query_coro(), timeout_seconds=5.0)
```

Raises `TimeoutError` if the coroutine exceeds the wall-clock limit.

---

## 4. Hybrid Retrieval (`vector_graph_hybrid.py`)

Combines vector similarity search with bounded BFS graph expansion.

### Pipeline

```
HybridQueryRequest
  │
  ▼ 1. Vector search (pgvector or ILIKE fallback)
  │    → candidate entities with vector_score ∈ [0, 1]
  │
  ▼ 2. BFS graph expansion (depth=max_depth, fan_out=max_fan_out)
  │    → adjacency_cache consulted before each DB hop
  │    → PostgresGraphProvider (SQL-limited) or InternalSQLProvider
  │
  ▼ 3. Score combination per entity
  │    combined = vector_score × 0.6 + graph_proximity × 0.4
  │
  ▼ 4. Rank, deduplicate, truncate → HybridQueryResult
```

### Scoring

| Component | Weight | Source |
|-----------|--------|--------|
| `vector_score` | 0.6 | Rank from cosine-distance or 0.5 for ILIKE hits |
| `graph_proximity` | 0.4 | `max(0, 1 − depth / max_depth)` |

### Example

```python
from app.services.agents.knowledge_graph.vector_graph_hybrid import (
    VectorGraphHybrid, HybridQueryRequest
)

hybrid = VectorGraphHybrid(db)
result = await hybrid.query(HybridQueryRequest(
    tenant_id="acme",
    text="incident response playbook",
    query_embedding=[0.1, 0.2, ...],  # optional
    limit=10,
    max_depth=2,
    max_fan_out=30,
    timeout_seconds=8.0,
))
print(result.context_block)
print(result.explain_plan)
```

`result.to_graph_result()` returns a `GraphQueryResult` compatible with the existing `GraphRAG` API.

---

## GraphStore Integration

No API changes. Existing callers of `GraphStore` automatically get:

- **Cache invalidation** on every `add_entity()` / `add_relation()` write.
- **Postgres provider** when `AGENT_KG_POSTGRES_GRAPH_ENABLED=true` (with safe fallback).

---

## Performance

Benchmark results are written to `artifacts/benchmarks/graphrag-dense-graph-benchmark.md` when the performance test suite runs.

```bash
pytest tests/unit/services/test_graphrag_optimizations.py -m performance -v
```

Expected (SQLite in CI, depth=2, fan_out=20):

| Metric | Target |
|--------|--------|
| Entity query (10k entities) | < 2 s |
| Hybrid GraphRAG query | < 5 s |

---

## Security

- Adjacency cache entries are **never serialised to disk** — they live in-process memory only.
- The cache is **per-tenant** — there is no shared state between tenants.
- Cache invalidation on write prevents stale data from persisting beyond the TTL.
