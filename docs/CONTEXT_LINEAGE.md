# Context Lineage

Phase 49 adds explainable context lineage for regulated retrieval.

## What is stored

The lineage graph stores only hashes and tenant-safe metadata:

- policy node
- document nodes
- chunk nodes
- retrieval node

No raw prompt or raw model response is stored.

## Integrity model

- Every lineage node gets a deterministic `node_hash`.
- The full lineage chain produces a `lineage_root_hash`.
- Retrieval proofs bind `lineage_root_hash` with `policy_hash`, `retrieval_sent_hash`, and a Merkle root.

## Replay and drift

Replay compares the original chunk participation set against replayed retrieval results:

- `stable`
- `minor_drift`
- `major_drift`

The replay record stores only hashed participation metadata and drift scores.
