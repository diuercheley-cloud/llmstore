---
owner: platform-ops
status: consolidated
---

# Remediation Adapter Sandbox

## Introduction
The Remediation Adapter Sandbox provides a secure, isolated environment for system-level actions. Every adapter must register a formal manifest that defines its capabilities and limitations.

## Manifest Definition
An `AdapterManifest` includes:
- **Adapter Name/Version:** Unique identifiers for the logic.
- **Allowed Capabilities:** List of specific actions the adapter is allowed to perform (e.g., `service_restart`, `log_cleanup`).
- **Denied Capabilities:** Explicit list of forbidden actions, which override any permissions.
- **Enforcement Flags:** Hard-coded flags that prevent network, subprocess, or unsandboxed activities.

## Sandbox Context
When a sandbox run is initiated, the system creates an `AdapterSandboxContext`. This context is:
- **Tenant-Isolated:** Cannot access data from other clients.
- **Immutable:** Constraints cannot be modified after creation.
- **Deterministic:** Ensures consistent outcomes for simulation.

## Policy Guarding
The `AdapterSandboxPolicyGuard` performs real-time inspection:
1. **Manifest Registration:** Checks if the manifest violates architectural mandates (e.g., trying to enable `network_access`).
2. **Execution Simulation:** Verifies if the requested action matches the adapter's capabilities and current context.

## Forbidden Capabilities (Sandbox Phase)
The following capabilities are architecturally blocked in the Phase 73 sandbox:
- `shell`: Any shell command execution.
- `subprocess`: Spawning external processes.
- `network`: Any outgoing or incoming network connection.
- `kubernetes_apply`: Raw Kubernetes manifest application.
- `filesystem_write_unscoped`: Writing outside of dedicated temp folders.

## Receipts and Proofs
Every sandbox activity generates an `AdapterSandboxReceipt`. These receipts provide a chain of verifiable evidence that:
- A specific manifest was registered with specific constraints.
- A simulation was performed within the bounds of that manifest.
- Any policy violations were detected and blocked.
