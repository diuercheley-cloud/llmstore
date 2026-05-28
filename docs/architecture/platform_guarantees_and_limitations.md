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

### Bounded Real Execution
- Agent runtime execution exists, but is feature-gated and disabled by default
- Plugin ABI defines contracts and now supports local sandboxed execution for installed plugins under explicit isolation policy
- Several enterprise/control-plane surfaces remain advisory, simulated, or operator-gated

### Local-Only PKI
- Local PKI issuance and certificate verification exist when explicitly enabled
- No external CA integration, formal trust anchor distribution, or certified key ceremony is implied
- Some cryptographic receipt and attestation surfaces still use placeholder signing outside the local PKI path

### No Hardware-Backed Trust
- Hardware-backed trust is not guaranteed by default
- No universal TPM, SEV, or SGX enforcement path exists across the platform
- Trust decisions remain advisory or operator-gated unless the operator enables and validates the underlying trust stack

### Bounded Plugin Execution
- Plugin runtime can execute installed plugin code locally in sandboxed mode
- Extension loader validates metadata, checksums, signatures, compatibility, and deterministic load ordering before activation
- Strong isolation via container/VM and distributed plugin execution are still not provided by default

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
- Any suggestion of unrestricted or cluster-wide third-party plugin code execution
- Any suggestion of mandatory cloud/SaaS

## Advisory Nature

Unless explicitly stated as "guaranteed," all platform behaviors are advisory:

- Validation results are advisory
- Policy decisions are advisory (default mode)
- Attestation is advisory (no hardware root of trust)
- Compatibility verification is advisory
- High-risk runs and side effects remain approval-gated by policy
