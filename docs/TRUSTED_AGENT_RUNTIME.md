---
owner: platform-ops
status: consolidated
---

# Trusted Agent Runtime

Phase 54 adds a tenant-scoped, policy-constrained agent execution layer for tools and actions that need to be auditable, replayable and approval-governed.

## Guarantees

- Deny-by-default tool execution: only tools present in `CommercialToolRegistry` are executable.
- Deterministic action plans: execution plans are normalized and hashed before runtime.
- Approval gates: sensitive tools produce `CommercialToolApproval` records and block execution until a decision exists.
- Per-action cryptographic receipts: each `CommercialAgentAction` gets a chained receipt hash and detached signature placeholder.
- Replay verification: `CommercialAgentReplayRecord` compares stored plan and graph hashes with recomputed values.
- Tenant isolation: agent profile scope, execution tenant and tool tenant scope must match.
- Confidential payload controls: payloads are redacted or hash-only in persisted metadata; plaintext logging is avoided.
- Immutable audit linkage: action receipts feed the financial audit chain and can be exported to offline bundles.

## Data Model

- `CommercialAgentExecution`: trusted runtime session, plan hash, graph hash, runtime snapshot hash, replay status and audit chain hash.
- `CommercialAgentAction`: each planned or executed tool action, with policy outcome, sandbox context and receipt.
- `CommercialToolRegistry`: trust registry, provenance fields, quotas and confidential payload policy.
- `CommercialToolApproval`: approval chain for gated actions.
- `CommercialAgentReplayRecord`: replay result and drift reason.

## APIs

Admin:

- `GET /admin/agents/runtime/status`
- `POST /admin/agents/runtime/plans`
- `POST /admin/agents/runtime/execute/{execution_id}`
- `GET /admin/agents/runtime/executions`
- `GET /admin/agents/runtime/actions/{execution_id}`
- `GET|POST /admin/agents/tools`
- `GET /admin/agents/tools/approvals`
- `POST /admin/agents/tools/approvals/{action_id}`
- `POST /admin/agents/replay/verify/{execution_id}`
- `GET /admin/agents/replay/records`
- `GET /admin/agents/replay/violations`

Portal:

- `GET /portal/agents/audit/executions`
- `GET /portal/agents/audit/executions/{execution_id}`
- `GET /portal/agents/audit/actions`
- `GET /portal/agents/audit/replay`
- `GET /portal/agents/audit/violations`

## Security Notes

- No `shell=True` execution path exists in the trusted runtime.
- The sandbox model is best-effort and policy-bound; it is not claimed to be inviolable.
- The current signature scheme is a local placeholder consistent with the existing receipt stack.
- The design is offline-compatible and avoids SaaS dependencies.

## Validation

Run:

```bash
make validate-trusted-agent-runtime
```
