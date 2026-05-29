# Memory Erasure Architecture

## Erasure Capabilities
The cognitive memory subsystems now officially support targeted **erasure events** and **tombstones**.

When a `request_erasure` action is triggered:
- The system resolves the `tenant_id` and optional `agent_id`, `user_id`, or `source` dimensions.
- Based on the strictness of the policy (`hard_delete` = `True` | `False`), rows are either wiped via cascading foreign keys or replaced by a deterministic tombstone.
- Tombstones clear all identifiable raw data, zero-out embedding vectors, but preserve the `AgentMemoryItem.id` and provenance dictionary to satisfy audit queries (Proof of Deletion).
- Erasure propagates immediately across standard vector indices and relation graphs.

Run `make memory-erasure-test` to validate these paths.
