# Platform Glossary

## Terms

### Advisory-Only
Default mode of operation where all validation results, policy decisions, and governance actions are informational. No enforcement occurs unless explicitly approved by an operator.

### Bounded Context
A logical boundary within the platform that encapsulates a specific domain capability. Contexts communicate through explicit contracts only. This term follows Domain-Driven Design conventions.

### Compatibility Contract
A formal versioned agreement between platform components that defines allowed interactions, capability negotiation, and deprecation lifecycle. Used in Phase 78 for cross-component compatibility verification.

### Deterministic
Property of an operation or system where identical inputs always produce identical outputs. The platform's event architecture, validation suite, and governance engine are all deterministic. This enables replay verification and reproducible audit.

### Dry-Run
A safe execution mode that validates operations without side effects. All platform operations default to dry-run. Real execution requires explicit operator approval.

### Federation
The capability for multiple independent platform instances to synchronize state and policies without requiring a central coordinator. Federation operates offline-first and supports intermittent connectivity.

### Governance Workflow
A structured, auditable process for policy evaluation, approval, and enforcement. Governance workflows are advisory-first and produce receipts for every decision.

### Lineage
The chain of provenance tracking how artifacts, events, or decisions were produced. Lineage includes source, transformation, and verification steps. Used in supply chain and audit contexts.

### Offline-First
Design principle where all core platform capabilities function without internet connectivity. Optional cloud features are additive, never mandatory. All validation, governance, and operations work offline.

### Placeholder Trust
Trust mechanisms that define contracts and interfaces without implementing real cryptographic trust. Used for attestation, PKI, and hardware trust — the platform defines what trust would look like without requiring real TPM, SEAL, or CA infrastructure.

### Plugin ABI
The formal binary interface contract that defines how plugins interact with the platform runtime. The ABI is defined and validated, but no real plugin execution occurs — it is a sandbox/placeholder.

### Policy Bundle
A versioned collection of governance policies that can be evaluated as a unit. Bundles support dry-run evaluation, conflict detection, and deterministic application order.

### Provenance
The documented origin and transformation history of an artifact, including build environment, dependencies, and verification steps. Used in supply chain and reproducible build contexts.

### Reproducible Build
A build process that produces bit-identical artifacts when given the same source code and build environment. The platform provides a framework for verifying reproducibility through hash comparison and receipt generation.

### Replay-Safe
Property of event logs and state transitions where replaying events produces identical outcomes without side effects. Replay safety is verified through deterministic event architecture and receipt chain validation.

### Sovereign
Principle that operators maintain full control over their platform instance — including data, models, policies, and execution — without vendor lock-in or mandatory telemetry.
