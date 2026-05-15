# Cryptographic Inference Receipts + Non-Repudiation (Phase 41)

## Overview

Provides cryptographic inference receipts for non-repudiation. Each inference
gets a signed, hash-chained receipt without storing prompt/response content.

## Receipt Model

### CommercialInferenceReceipt

| Field | Description |
|-------|-------------|
| `id` | UUID primary key |
| `prompt_hash` | SHA-256 of prompt (full content never stored) |
| `response_hash` | SHA-256 of response (full content never stored) |
| `receipt_hash` | SHA-256 of all receipt fields (self-hash) |
| `previous_receipt_hash` | Links to previous receipt in chain |
| `detached_signature` | Placeholder detached signature |
| `timestamp_mode` | `local`, `offline_tsa`, or `external_placeholder` |
| `verification_status` | `pending`, `verified`, `failed`, `tampered` |

### CommercialInferenceReceiptLedgerEvent

Immutable audit trail for all receipt lifecycle events.

### CommercialInferenceReceiptVerificationReport

Stores verification results including chain validity, signature status,
runtime matching, and replay drift detection.

## Chain Hashing

Each receipt hash incorporates the previous receipt hash when
`COMMERCIAL_RECEIPTS_CHAINING_ENABLED=true` (default). This creates an
immutable chain: breaking any link invalidates all subsequent receipts.

### Build

```
receipt_hash = SHA-256(canonical_json({
  prompt_hash,
  response_hash,
  previous_receipt_hash (or null),
  ...
}))
```

## Detached Signatures

Signatures are detached from the receipt data. The current implementation
uses `ed25519_placeholder` — a deterministic placeholder that does **not**
constitute formal PKI.

**Config**: `COMMERCIAL_RECEIPT_SIGNATURE_ALGORITHM=ed25519_placeholder`

## Timestamping

Three modes:

| Mode | Description |
|------|-------------|
| `local` | Local signed timestamp (no external authority) |
| `offline_tsa` | Offline timestamp token (local best-effort) |
| `external_placeholder` | Placeholder for future TSA integration |

No external SaaS dependency.

## Replay Linkage

Receipts can reference `reproducibility_record_id` to link with
reproducibility records. Verification reports include `replay_match`
and `runtime_match` fields.

## Verification Reports

Generated on demand. Fields:
- `verification_result`: `valid`, `invalid`, `partial`
- `chain_valid`: Whether the hash chain is intact
- `signature_valid`: Whether the detached signature is present
- `runtime_match`: Whether runtime snapshot matches
- `replay_match`: Whether replay result matches
- `drift_detected`: True if runtime or replay drift

## Tenant Verification

Tenants can:
- List their receipts (`GET /portal/inference/receipts`)
- View individual receipts (`GET /portal/inference/receipts/{id}`)
- Trigger verification (`POST /portal/inference/receipts/{id}/verify`)

Prompts/responses are never exposed.

## Endpoints

### Admin
- `GET /admin/inference/receipts`
- `GET /admin/inference/receipts/{id}`
- `POST /admin/inference/receipts/{id}/verify`
- `POST /admin/inference/receipts/{id}/export`
- `POST /admin/inference/receipts/validate-chain`
- `GET /admin/inference/receipt-ledger`
- `GET /admin/inference/receipt-verification-reports`

### Portal (tenant-safe)
- `GET /portal/inference/receipts`
- `GET /portal/inference/receipts/{id}`
- `POST /portal/inference/receipts/{id}/verify`

## Configuration

```env
COMMERCIAL_RECEIPTS_ENABLED=true
COMMERCIAL_RECEIPTS_CHAINING_ENABLED=true
COMMERCIAL_RECEIPTS_TIMESTAMP_MODE=local
COMMERCIAL_RECEIPTS_EXPORT_ENABLED=true
COMMERCIAL_RECEIPTS_SIGNATURE_REQUIRED=false
COMMERCIAL_RECEIPT_SIGNATURE_ALGORITHM=ed25519_placeholder
```

## Limitations

- **No formal PKI**: signatures use placeholder algorithms
- **No legal TSA**: timestamps are local best-effort
- **No SaaS dependency**: all operations local
- **Best-effort replay**: cross-hardware determinism not guaranteed
- **No prompt/response storage**: only hashes are retained

## Non-Repudiation Caveats

- Detached signatures are **not** legally binding
- Timestamp tokens have **no** external authority
- Chain integrity depends on database immutability
- Formal non-repudiation requires external PKI + TSA integration
