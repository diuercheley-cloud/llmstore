# Verifiable AI Execution Proofs + Merkle Audit Timelines

## Overview

This document describes the **Phase 42** (codename Phase 60) implementation of verifiable AI execution proofs and Merkle audit timelines in the LLM Inference Stack.

The goal is to provide cryptographic, auditable proof that inference executions occurred as recorded — without exposing prompts, responses, or any customer-sensitive content.

## Architecture

### Merkle Timeline

A **Merkle Timeline** is a time-bucketed Merkle tree built from inference-related events (receipts, replay events, runtime scans, etc.).

- Each event becomes a **leaf** in the tree.
- Leaves are hashed with canonical SHA256 over a JSON payload sorted by keys.
- The tree is built bottom-up, padding leaves to the next power of two by duplicating the last leaf if needed.
- The final **Merkle root** represents the entire timeline.

### Timeline Types

| Type | Description |
|------|-------------|
| `inference_receipts` | Cryptographically signed inference receipts |
| `replay_events` | Replay verification results |
| `runtime_integrity` | Runtime snapshot checksums |
| `policy_events` | Governance / policy events (reserved) |
| `financial_events` | Financial audit events (reserved) |

### Timeline Sealing

Once a timeline is "sealed":
- It becomes **immutable**.
- The Merkle root is finalized.
- Any modification to a leaf invalidates the root, making tampering detectable.
- The next timeline can optionally reference the previous timeline's root, forming a **chain**.

### Inclusion Proof

For any leaf in a sealed timeline, an **inclusion proof** can be generated:

1. Start with the leaf hash.
2. Walk up the tree, combining with sibling hashes at each level.
3. The final recomputed hash must equal the Merkle root.

This proves that the specific event was included in the timeline, without revealing other leaves.

### Execution Proof Bundle

An **Execution Proof** is a portable bundle that includes:

- Receipt hash (not the receipt content)
- Signature verification status
- Merkle inclusion proof
- Timeline root
- Previous timeline root (for chain validation)
- Runtime snapshot hash
- Model manifest hash
- Replay verification summary
- Timestamp summary

**No prompt or response content is included.**

## Data Models

### `CommercialMerkleTimeline`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `timeline_type` | enum | One of the timeline types |
| `period_start` | datetime | Window start |
| `period_end` | datetime | Window end |
| `leaf_count` | int | Number of leaves |
| `merkle_root` | string | SHA256 hex root |
| `previous_timeline_root` | string (nullable) | Previous root for chaining |
| `timeline_hash` | string | Combined hash of metadata |
| `status` | enum | `building`, `sealed`, `verified`, `invalid` |
| `sealed_at` | datetime (nullable) | When sealed |

### `CommercialMerkleLeaf`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `timeline_id` | UUID FK | Parent timeline |
| `source_type` | enum | Type of source event |
| `source_id` | string | ID of the source record |
| `leaf_hash` | string | SHA256 hash of canonical leaf |
| `leaf_index` | int | Position in the tree |
| `metadata_json` | JSON | Sanitized metadata (no prompts/responses) |

### `CommercialExecutionProof`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `receipt_id` | UUID FK (nullable) | Related receipt |
| `timeline_id` | UUID FK | Parent timeline |
| `proof_type` | enum | `inclusion`, `execution`, `replay`, `runtime`, `full` |
| `proof_json` | JSON | The proof bundle |
| `proof_hash` | string | SHA256 of the canonical proof JSON |
| `verification_status` | enum | `pending`, `valid`, `invalid`, `partial` |
| `created_at` | datetime | Creation timestamp |
| `verified_at` | datetime (nullable) | Verification timestamp |

## API Endpoints

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/inference/proofs/timelines` | List timelines |
| POST | `/admin/inference/proofs/timelines/build` | Build a new timeline |
| POST | `/admin/inference/proofs/timelines/{id}/seal` | Seal a timeline |
| POST | `/admin/inference/proofs/timelines/{id}/verify` | Verify timeline integrity |
| GET | `/admin/inference/proofs/proofs` | List execution proofs |
| POST | `/admin/inference/proofs/proofs/generate/{receipt_id}` | Generate proof for receipt |
| POST | `/admin/inference/proofs/proofs/{id}/verify` | Verify a proof |
| GET | `/admin/inference/proofs/proofs/{id}/export` | Export tenant-safe proof |

### Portal Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portal/inference/proofs/proofs` | List proofs (tenant-safe) |
| GET | `/portal/inference/proofs/proofs/{id}` | Get proof (tenant-safe) |
| POST | `/portal/inference/proofs/proofs/{id}/verify` | Verify proof |

## Verification Workflow

1. **Build Timeline**: Collect events in a window and compute Merkle root.
2. **Seal Timeline**: Finalize the root, mark as immutable.
3. **Generate Inclusion Proof**: For any receipt, produce a Merkle proof.
4. **Generate Execution Proof**: Bundle inclusion proof + metadata into a portable proof.
5. **Verify Proof**: Recompute the Merkle path and check chain integrity.
6. **Export Proof**: Produce a tenant-safe JSON for external verification.

## Configuration

```env
COMMERCIAL_MERKLE_TIMELINES_ENABLED=true
COMMERCIAL_MERKLE_TIMELINE_WINDOW_MINUTES=60
COMMERCIAL_MERKLE_TIMELINE_AUTO_SEAL=false
COMMERCIAL_EXECUTION_PROOFS_ENABLED=true
COMMERCIAL_EXECUTION_PROOFS_EXPORT_ENABLED=true
```

## Limitations

- **No blockchain**: This is a centralized Merkle proof system, not a public blockchain. Trust is anchored in the control plane's signing key and audit logs.
- **Best-effort determinism**: Replay verification is best-effort; hardware and software differences can cause non-deterministic outputs.
- **No prompt/response exposure**: By design, proofs never include raw prompts or completions. Only hashes and verification status are exposed.
- **Tenant isolation**: Portal endpoints filter by tenant. Admin endpoints require admin authentication.
- **No external SaaS dependency**: All proof generation and verification happens locally.

## Security Considerations

- **Tamper detection**: Modifying any leaf after sealing changes the Merkle root, invalidating inclusion proofs.
- **Chain validation**: Timeline chaining ensures a history of sealed roots. A break in the chain indicates tampering or rollback.
- **Sanitized exports**: Exported proofs are scrubbed of any sensitive fields before leaving the system.

## Next Steps

- Public Verifier CLI / offline verification tool
- Integration with third-party notarization services (optional)
- Cross-tenant proof verification for consortium scenarios
