---
owner: platform-ops
status: consolidated
---

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

### Plugin ABI Sandbox
- Plugin ABI defines contracts and supports local sandboxed execution for installed plugins under explicit isolation policy
- Extension loader validates metadata, checksums, signatures, compatibility, and deterministic load ordering before activation
- Strong isolation via container/VM and distributed plugin execution are still not provided by default

### Local PKI
- Local PKI issuance and certificate verification exist when explicitly enabled
- No external CA integration, formal trust anchor distribution, or formal key ceremony is implied
- Cryptographic receipt and sandbox attestation surfaces use real Ed25519 signing, and stubs/placeholders are strictly blocked in production.

### Policy-Based Attestation
- Hardware-backed trust is not guaranteed by default
- No universal TPM, SEV, or SGX enforcement path exists across the platform
- Trust decisions remain advisory or operator-gated unless the operator enables and validates the underlying trust stack

### Offline-First
- Federation is optional and offline-first
- No cross-cluster consensus required
- Each node operates independently

### Evidence-Driven Compliance
- Validation is cryptographic and externally verifiable
- No external audit or certification body
- Compliance is operator-responsibility

## Prohibited Claims

The following claims must never appear in documentation:

- `military-grade` or similar security claims
- `guaranteed secure` or absolute security guarantees
- `certified` or `formally certified` without explicit evidence
- `unbreakable` or `impenetrable`
- Any suggestion of real PKI or hardware trust
- Any suggestion of unrestricted or cluster-wide third-party plugin code execution
- Any suggestion of mandatory cloud/SaaS

## Advisory Nature

Unless explicitly stated as "guaranteed," platform behaviors follow an advisory-first pattern:

- Validation results are enforced in production-ready surfaces.
- Policy decisions are advisory by default (dry-run mode).
- Attestation and hardware-backed trust require explicit operator configuration.
- Compatibility verification is advisory unless gated by a promotion policy.
- High-risk runs and side effects remain approval-gated by policy.
