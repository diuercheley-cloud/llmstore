# Federated Deterministic Workflows

Phase 57 extends deterministic workflows to a federated multi-cluster model without relying on external SaaS services.

## Guarantees

- Deterministic DAG partitioning and stage ownership.
- Tenant-scoped cluster isolation.
- Immutable hash chaining for executions, peers, leases, consensus events, and replay reports.
- Metadata-only storage for federated state; prompts, responses, secrets, and sensitive payloads stay redacted.
- Cross-region replay validation and drift detection.
- Sovereign and air-gapped compatibility through signed offline bundles and offline CRL enforcement.

## Federation Modes

- `local_only`: no forwarding, local verification only.
- `push`: source cluster pushes sanitized execution metadata to peers.
- `pull`: peer pulls sanitized execution metadata from source.
- `hybrid`: deterministic mix of push and pull with quorum validation.
- `sovereign_airgap`: transfer only via signed offline bundles and local trust enforcement.

## Core Components

- `commercial_federated_workflow_executions`: top-level federated execution record.
- `commercial_workflow_execution_peers`: trusted peer participation and cluster topology.
- `commercial_workflow_execution_leases`: deterministic lease election and failover.
- `commercial_workflow_consensus_events`: quorum and reconciliation ledger.
- `commercial_workflow_replay_federation_reports`: signed replay verification artifacts.

## Governance Integration

Each federated execution captures:

- active policy enforcement hash
- governance decision trail
- confidential-runtime compatibility summary
- signed execution receipt and signed stage receipts

## Operational Validation

Run:

```bash
make validate-federated-workflows
```
