---
owner: platform-ops
status: consolidated
---

# Regulated RAG Vault + Confidential Retrieval Fabric

## Overview
Phase 53 implements a highly secure, tenant-isolated Retrieval-Augmented Generation (RAG) architecture. It is designed for regulated environments where vector embeddings, document chunks, and retrieval logs must never leak plaintext context and must be cryptographically auditable.

## Core Mechanisms

### 1. Tenant-Scoped Vaults
- Each tenant is assigned a `CommercialRAGVault`.
- Cryptographic boundaries prevent cross-tenant retrieval. If a session bound to Tenant A attempts to retrieve chunks from Tenant B's vault, the `ContextSanitizer` blocks the action and logs a `cross_tenant` policy violation.

### 2. Confidential Lineage & Hashes
- **No Plaintext in DB**: Document contents and chunks are never stored in plaintext within the control plane databases. Only `document_hash` and `chunk_hash` are retained.
- **Lineage Tracking**: A `CommercialRAGChunk` can always be traced back to its parent `CommercialRAGDocument` and the originating `CommercialRAGVault`, enabling precise provenance auditing.

### 3. Retrieval Receipts
- Every retrieval operation generates a `CommercialRetrievalReceipt`.
- This receipt cryptographically binds the `session_id`, the `query_hash`, and the list of retrieved `chunk_hashes`.
- This provides an immutable audit trail proving exactly what context was provided to the LLM during generation, critical for legal and compliance reviews.

### 4. Policy-Aware Retrieval
- Documents have classifications (e.g., `internal`, `confidential`, `restricted`).
- The `ContextSanitizer` enforces retrieval policies post-search but pre-generation. If a restricted document is retrieved in a context that does not allow it, it is redacted from the final prompt.

## API Integration
- `GET /admin/rag/vaults`: Monitor tenant isolation bounds.
- `GET /admin/rag/receipts`: View the immutable retrieval audit trail.
- `GET /admin/rag/lineage/{chunk_hash}`: Trace the provenance of a specific chunk.
- `GET /admin/rag/violations`: Monitor blocked retrieval attempts.

## Compliance
This architecture aligns with strict data residency and privacy mandates (e.g., GDPR, HIPAA, ITAR) by ensuring that the control plane only routes mathematical representations (hashes and encrypted embeddings) rather than raw sensitive data.
