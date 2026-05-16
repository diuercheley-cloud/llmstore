# Platform Module Relationships

## Module Dependency Graph

```mermaid
graph TB
    subgraph "Phase 69-72: Operations Foundation"
        P69[Failure Forecasting]
        P70[Correlation Engine]
        P71[Remediation Planning]
        P72[Remediation Execution]
    end

    subgraph "Phase 73-75: Adapter System"
        P73[Adapter Sandbox]
        P74[Signed Adapter Registry]
        P75[Adapter Promotion]
    end

    subgraph "Phase 76: Attestation"
        P76[Attestation Framework]
    end

    subgraph "Phase 77-78: Federation"
        P77[Federation Sync]
        P78[Compatibility Contracts]
    end

    subgraph "Phase 79-81: Plugin & Supply Chain"
        P79[Plugin ABI Runtime]
        P80[Plugin Supply Chain]
        P81[Reproducible Builds]
    end

    subgraph "Phase 82: Sustainability"
        P82[Platform Sustainability]
    end

    P69 --> P70
    P70 --> P71
    P71 --> P72
    P72 --> P73
    P73 --> P74
    P74 --> P75
    P75 --> P76
    P76 --> P77
    P77 --> P78
    P78 --> P79
    P79 --> P80
    P80 --> P81
    P81 --> P82

    P76 --> P82
    P77 --> P82
    P78 --> P79
```

## Module Dependency Table

| Module | Depends On | Used By |
|--------|-----------|---------|
| Phase 69: Failure Forecasting | — | Phase 70 |
| Phase 70: Correlation Engine | Phase 69 | Phase 71 |
| Phase 71: Remediation Planning | Phase 70 | Phase 72 |
| Phase 72: Remediation Execution | Phase 71 | Phase 73, Phase 82 |
| Phase 73: Adapter Sandbox | Phase 72 | Phase 74 |
| Phase 74: Adapter Registry | Phase 73 | Phase 75 |
| Phase 75: Adapter Promotion | Phase 74 | Phase 76 |
| Phase 76: Attestation Framework | Phase 75 | Phase 77, Phase 82 |
| Phase 77: Federation Sync | Phase 76 | Phase 78, Phase 82 |
| Phase 78: Compatibility Contracts | Phase 77 | Phase 79 |
| Phase 79: Plugin ABI | Phase 78 | Phase 80 |
| Phase 80: Plugin Supply Chain | Phase 79 | Phase 81 |
| Phase 81: Reproducible Builds | Phase 80 | Phase 82 |
| Phase 82: Platform Sustainability | Phase 72, 76, 77, 81 | — |

## Cross-Cutting Concerns

### Deterministic Event Architecture
Spans all phases. Every phase produces deterministic events that feed into the correlation engine, attestation framework, and replay verification.

### Governance
The governance engine consumes events from all phases and produces policy decisions. Governance is advisory-first: all decisions are dry-run by default.

### Security & Trust
Security boundaries are defined across all phases but no phase implements real PKI, hardware-backed trust, or real plugin execution.

### Validation
Each phase includes its own validation scripts and tests. The aggregate validation targets (`validate-architecture-smoke`, `validate-architecture-full`) compose all phase validators in deterministic order.

## Key Architectural Invariants

1. No circular dependencies between bounded contexts
2. All phase validations run offline
3. No phase introduces mandatory SaaS dependencies
4. No phase implements real execution — only contracts and validation
5. All state changes produce immutable, versioned events
6. All cross-context communication uses explicit contracts
