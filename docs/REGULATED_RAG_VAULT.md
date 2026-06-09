---
owner: platform-ops
status: consolidated
---

# Regulated RAG Vault

Phase 48 adds a governed retrieval layer for regulated workloads without breaking the existing OpenAI-compatible APIs.

## What it does

- Creates tenant-scoped regulated vaults for RAG documents and chunks.
- Enforces tenant isolation, ACL checks, ABAC checks, legal holds, signed-document requirements, confidential-runtime requirements and trusted-model requirements before retrieval reaches the model.
- Avoids storing sensitive plaintext in the legacy retrieval index when classification requires protection. In restricted modes, legacy chunks store only a redacted marker while the regulated vault keeps the encrypted payload.
- Records immutable retrieval audit hashes without storing prompt or response plaintext.
- Adds poisoning heuristics for prompt injection, authority mimicry, cross-tenant attempts and abnormal retrieval patterns.

## Data model

- `CommercialRAGVault`
- `CommercialRAGDocument`
- `CommercialRAGChunk`
- `CommercialRAGAccessPolicy`
- `CommercialRAGRetrievalAudit`
- `CommercialRAGPoisoningAlert`
- `CommercialRAGLegalHold`

Migration: `control_plane/alembic/versions/20260515_0061_regulated_rag_vault.py`

## Config

Defaults:

- `COMMERCIAL_RAG_VAULT_ENABLED=false`
- `COMMERCIAL_RAG_POLICY_MODE=report_only`
- `COMMERCIAL_RAG_VAULT_REQUIRE_CONFIDENTIAL_RUNTIME=false`
- `COMMERCIAL_RAG_VAULT_REQUIRE_SIGNED_DOCUMENTS=false`
- `COMMERCIAL_RAG_MAX_CONTEXT_CHUNKS=20`
- `COMMERCIAL_RAG_VAULT_ENABLE_POISON_DETECTION=true`
- `COMMERCIAL_RAG_VAULT_ENABLE_IMMUTABLE_AUDIT=true`

## Admin endpoints

- `GET /admin/rag/vaults`
- `POST /admin/rag/vaults`
- `GET /admin/rag/documents`
- `POST /admin/rag/documents`
- `GET /admin/rag/retrieval-audit`
- `GET /admin/rag/poison-alerts`
- `POST /admin/rag/poison-alerts/{id}/resolve`
- `GET /admin/rag/legal-holds`
- `POST /admin/rag/legal-holds`

## Portal visibility

- `GET /portal/rag/vault`
- `GET /portal/rag/retrieval-history`
- `GET /portal/rag/legal-holds`
- `GET /portal/rag/trust-status`

## Validation

```bash
pytest -q \
  tests/test_rag_vault.py \
  tests/test_rag_access_control.py \
  tests/test_rag_poison_detection.py \
  tests/test_rag_retrieval_audit.py

bash -n scripts/validate-rag-vault.sh
make validate-rag-vault
```
