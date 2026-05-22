# Semantic Memory

## Overview

Semantic memory enables agents to retrieve relevant information from past interactions using vector embeddings and cosine similarity, rather than naive SQL `LIKE` matching.

## Architecture

```
User Query
    |
    v
MemoryRetriever.retrieve()
    |
    ├── MemoryIndexingService.search(semantic=True)
    |       ├── Compute query embedding (mock | local)
    |       ├── Fetch stored embeddings from AgentMemoryIndex
    |       └── Cosine similarity rank → top-K items
    |
    ├── Retention filter (expired items excluded)
    ├── Consent filter (long_term only, checks MemoryConsent)
    ├── Redaction (PII/secret masking via MemoryRedaction)
    └── Score threshold filter (configurable via policy)
    |
    v
List[MemoryRetrievalResult]  (sorted by score DESC)
```

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED` | `false` | Enables vector-based search instead of LIKE |
| `AGENT_MEMORY_EMBEDDINGS_PROVIDER` | `mock` | `mock` (deterministic SHA-256), `local` (sentence-transformers) |

## Embedding Providers

### `mock` (default)
Deterministic, zero-dependency embeddings via SHA-256. Suitable for development, testing, and CI. **Does not require any ML model.**

### `local`
Uses `sentence-transformers` with `all-MiniLM-L6-v2` model. Falls back to mock if the model fails to load.

## Tenant Isolation

Every query filters by `tenant_id` and `agent_id`. The semantic search query:

```python
stmt = select(AgentMemoryIndex, AgentMemoryItem).join(
    AgentMemoryItem, AgentMemoryIndex.memory_item_id == AgentMemoryItem.id
).where(
    AgentMemoryIndex.tenant_id == tenant_id,
    AgentMemoryIndex.agent_id == agent_id,
    AgentMemoryIndex.embedding.isnot(None),
    AgentMemoryIndex.index_status == "completed",
)
```

Cross-tenant memory access is structurally impossible.

## Scoring

Cosine similarity is computed in Python:

```python
def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x*x for x in a))
    norm_b = sqrt(sum(y*y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
```

Results are sorted descending by score. Items below `score_threshold` are excluded.

## Indexing

When a memory is written, `MemoryIndexingService.index_item()`:
1. Computes the embedding vector (384 dimensions) via the configured provider
2. Stores it as JSON in `AgentMemoryIndex.embedding`

```python
embedding = await self._compute_embedding(content)
index = AgentMemoryIndex(
    tenant_id=tenant_id,
    agent_id=agent_id,
    memory_item_id=item.id,
    index_status="completed",
    embedding=json.dumps(embedding),
)
```

## Usage

```python
service = AgentMemoryService(db)

results = await service.semantic_search_memory(
    tenant_id=tenant_id,
    agent_id=agent_id,
    query="user preferences",
    memory_type="long_term",
    user_id=user_id,
    top_k=5,
    score_threshold=0.3,
)
```

## Testing

- `test_semantic_search_returns_relevant_memory` — semantic search finds match
- `test_like_fallback_works_in_mock` — LIKE fallback when semantic disabled
- `test_tenant_isolation_semantic_search` — no cross-tenant leakage
- `test_cosine_similarity_basic` — math correctness
- `test_mock_embedding_deterministic` — deterministic output
