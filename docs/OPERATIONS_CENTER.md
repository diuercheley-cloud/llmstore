---
owner: platform-ops
status: consolidated
---

# Operations Center

The Operations Center builds a deterministic, cryptographically verifiable Trust Graph across governance, runtime fabric, workflows, receipts, federation, sovereign controls, confidential runtime, and model supply chain state.

## Guarantees

- Deterministic graph serialization and graph hashing.
- Merkle-linked topology rooted in node lineage hashes and edge hashes.
- Snapshot `immutable_hash` chaining through `previous_snapshot_hash`.
- Sanitized exports only; no plaintext prompts, responses, tokens, or secrets.
- Tenant-aware graph construction and trust violation detection.
- Sovereign redaction in graph/export payloads.
- Offline-capable exports for air-gapped verification.

## Core Models

- `CommercialTrustGraphNode`
- `CommercialTrustGraphEdge`
- `CommercialOperationsCenterEvent`
- `CommercialCryptographicTrustSnapshot`
- `CommercialTrustViolation`

## Services

- `app/services/security/trust_graph.py`
  Builds the unified graph from SQLAlchemy-backed local state and manual trust nodes.
- `app/services/security/cryptographic_topology.py`
  Calculates Merkle-linked topology, federation maps, sovereign subgraphs, runtime integrity timelines, and replay lineage views.
- `app/services/security/trust_snapshotting.py`
  Creates cryptographic snapshots, event chain entries, and export bundles.
- `app/services/security/trust_violation_detection.py`
  Detects hash mismatches, missing lineage, tenant isolation failures, dependency integrity issues, and snapshot chain breaks.

## Integrated Domains

- Governance Federation
- Runtime Fabric
- Cryptographic Receipts
- Deterministic Workflows
- Sovereign Appliance / Air-gap packages
- Confidential Runtime
- Policy Governance
- Model Supply Chain

## API

- `GET /admin/ops-center/graph`
- `POST /admin/ops-center/snapshot`
  Supports `format=record|json|signed_bundle|offline_audit_package`
- `GET /admin/ops-center/trust-violations`
- `GET /admin/ops-center/lineage`
- `GET /admin/ops-center/integrity`
- `GET /admin/ops-center/federation-map`

## Export Formats

- `json`
  Sanitized snapshot payload plus manifest hash.
- `signed_bundle`
  Sanitized export plus detached local placeholder signature for offline chain verification.
- `offline_audit_package`
  Air-gap-ready package metadata, immutable snapshot payload, and verification instructions.

## Verification Flow

1. Fetch or generate a snapshot.
2. Recompute the snapshot hash from sanitized payload.
3. Validate `immutable_hash`.
4. Validate `previous_snapshot_hash` chaining across snapshots.
5. Recompute graph `merkle_root` from nodes and edges.
6. Review trust violations and runtime integrity timeline.

## Security Notes

- No Neo4j and no cloud dependency.
- SQLAlchemy plus local structures only.
- No secret-bearing fields are exported.
- Sovereign hashes are truncated/redacted in exported graph payloads where required.
- The feature is designed to remain useful even when snapshot/event persistence tables are unavailable in constrained test environments.
