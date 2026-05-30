# Semantic Memory Retrieval

This document describes the implementation and configuration of real semantic memory retrieval in the Agentic AI Platform.

## Overview
Semantic memory retrieval replaces simple text matching with vector-based similarity search. This allows agents to retrieve relevant memories even when queries don't use the exact same words as the stored memories.

## Feature Flags
- `AGENT_SEMANTIC_MEMORY_ENABLED=true`: Enables the semantic retrieval path.
- `AGENT_MEMORY_VECTOR_PROVIDER`: Choices are `pgvector`, `chroma`, or `mock`.
- `AGENT_MEMORY_EMBEDDINGS_PROVIDER`: Provider for computing vectors (e.g., `local`, `openai`, `mock`).

## Vector Store Providers

### 1. PostgreSQL (pgvector)
Uses the `pgvector` extension in PostgreSQL for efficient vector similarity search directly in the database.
- **Isolation**: Tenant and Agent isolation is enforced via SQL `WHERE` clauses.
- **Score**: Supports Cosine Distance and Inner Product.

### 2. ChromaDB
Uses ChromaDB as a dedicated vector database.
- **Isolation**: Enforced via tenant-specific collections and metadata filtering.
- **Metadata**: Stores agent IDs and memory types as metadata for filtered retrieval.

### 3. Mock (Fallback)
An in-memory provider used for development or as a safety fallback.
- **Behavior**: Performs in-memory cosine similarity calculation.
- **Marking**: Results from the mock provider are explicitly marked with `provider: mock`.

## Retrieval Process

### 1. Embedding Computation
Every query is first converted into a vector embedding using the configured embedding service.

### 2. Vector Search
The query embedding is sent to the selected `VectorStore` provider, which returns the `top_k` matches that meet the `score_threshold`.

### 3. Hydration & Validation
The results are hydrated from the primary database (`AgentMemoryItem`) to ensure that:
- The memory hasn't been deleted (Erasure/Right to be Forgotten).
- The memory belongs to the correct tenant.
- Any necessary redactions are applied to the content.

### 4. Provenance
Each retrieved memory includes provenance metadata:
- `score`: The similarity score.
- `provider`: Which vector store provided the result.
- `memory_type`: Long-term, episodic, etc.

## Security
- **Tenant Isolation**: Strictly enforced at the vector store level.
- **Injection Audit**: Memory indexing and retrieval logs are audited for suspicious patterns.
- **Score Threshold**: Prevents injecting low-confidence or irrelevant context into the agent.
