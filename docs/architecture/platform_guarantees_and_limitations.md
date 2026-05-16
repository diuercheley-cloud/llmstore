# Platform Guarantees and Limitations

## Guarantees

### Deterministic Operations
- All core operations produce deterministic outputs given identical inputs
- Event logs are structured, versioned, and replayable
- Governance decisions are reproducible from event history alone

### Replay Safety
- State transitions can be fully replayed from event logs
- Replay does not depend on external services or network
- Receipt chain validation is self-contained per node

### Offline-First
- All validation scripts and tests run without internet
- No mandatory SaaS or cloud dependencies
- Federation sync is designed for intermittent connectivity

### Sovereign Control
- Operators control all data, models, and policies
- No mandatory telemetry or vendor lock-in
- Full export and deletion capabilities

### Advisory-First Governance
- Policy engine runs in advisory mode by default
- Enforcement requires explicit operator approval
- All governance actions produce auditable receipts

### Bounded Context Isolation
- Contexts communicate through explicit contracts only
- Domain boundaries are validated by automated tests
- No circular dependencies between bounded contexts

## Explicit Limitations

### No Real Execution
- No real runtime execution — runtime abstractions are advisory placeholders
- Plugin ABI defines contracts but does not execute plugins
- Adapter sandbox validates manifests, not real execution

### No Real PKI
- Certificate operations are simulated
- No CA integration or real certificate issuance
- Cryptographic receipts use placeholder signing

### No Hardware-Backed Trust
- Attestation framework is policy-only
- No TPM, SEV, or SGX integration
- Trust decisions are advisory and operator-gated

### No Real Plugin Execution
- Plugin ABI defines interface contracts only
- Extension loader validates metadata, not runtime behavior
- No sandboxed process execution

### No Formal Certification
- Validation is advisory and self-attested
- No external audit or certification body
- Compliance is operator-responsibility

### No Mandatory Federation
- Federation is optional and offline-first
- No cross-cluster consensus required
- Each node operates independently

## Prohibited Claims

The following claims must never appear in documentation:

- `military-grade` or similar security claims
- `guaranteed secure` or absolute security guarantees
- `certified` or `formally certified` without explicit evidence
- `unbreakable` or `impenetrable`
- Any suggestion of real PKI or hardware trust
- Any suggestion of real plugin execution
- Any suggestion of mandatory cloud/SaaS

## Advisory Nature

Unless explicitly stated as "guaranteed," all platform behaviors are advisory:

- Validation results are advisory
- Policy decisions are advisory (default mode)
- Attestation is advisory (no hardware root of trust)
- Compatibility verification is advisory
- All "runs" are dry-runs unless operator explicitly approves
