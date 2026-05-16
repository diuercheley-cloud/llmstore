# Phase 73: Controlled Adapter Sandbox

## Overview
Phase 73 introduces a formal, deterministic sandbox environment for remediation adapters. This phase establishes the contracts and manifests required for any system-level interaction, ensuring that all future real infrastructure execution occurs within strictly auditably and safe boundaries.

**Crucial Note:** In Phase 73, the sandbox is **simulation-only**. All external system access, network calls, and subprocess execution are architecturally blocked.

## Objectives
- Define a formal `AdapterContract` and `AdapterManifest` for all remediation activities.
- Implement a `SandboxExecutionContext` to isolate adapter logic.
- Enforce strict policy guards against forbidden capabilities (shell, network, etc.).
- Simulate adapter execution results deterministically.
- Generate cryptographically-verifiable receipts for manifest registration and sandbox runs.
- Integrate sandbox monitoring into the dashboards.

## Architectural Principles
1. **Sandboxing by Default:** `sandbox_required=True` is a hard requirement for all manifests.
2. **Zero-Trust Capabilities:** Network, subprocess, and external system access are strictly forbidden (`False`) in this phase.
3. **Denied over Allowed:** Denied capabilities in the manifest always override any allowed capabilities.
4. **Deterministic Simulation:** Same input manifest and steps always yield the same logical simulation result.
5. **Policy Guarding:** A dedicated `AdapterSandboxPolicyGuard` inspects every manifest and execution request.
6. **Immutable Receipts:** Every sandbox run and manifest registration is backed by an immutable receipt.

## Components

### Data Model
- `AdapterManifest`: Formal definition of an adapter's identity and capabilities.
- `AdapterSandboxRun`: Lifecycle tracking for a specific sandbox simulation.
- `AdapterSandboxStepResult`: Granular results of simulated adapter actions.
- `AdapterSandboxPolicyViolation`: Records of blocked or dangerous activities.
- `AdapterSandboxReceipt`: Verifiable proofs for auditing.

### Services
- `AdapterManifestValidator`: Ensures manifests comply with architectural mandates.
- `AdapterSandboxSimulationRunner`: Core engine for safe simulation.
- `AdapterSandboxPolicyGuard`: Real-time inspector for dangerous activities.
- `AdapterSandboxContext`: Encapsulates the runtime constraints.

### API
- `POST /admin/operations/adapter-sandbox/manifests`: Registers and validates a new manifest.
- `POST /admin/operations/adapter-sandbox/runs/prepare`: Prepares a new sandbox run.
- `POST /admin/operations/adapter-sandbox/runs/simulate`: Executes a deterministic simulation.
- `GET /admin/operations/adapter-sandbox/violations`: Lists detected policy violations.

## Security & Compliance
- **Isolamento de Tenant:** All manifests and sandbox runs are strictly scoped to a specific `client_id`.
- **Policy Enforcement:** Any attempt to enable forbidden capabilities results in a blocked manifest and an audit event.
- **Offline-First:** All validation and simulation logic is local, requiring no external connectivity.
