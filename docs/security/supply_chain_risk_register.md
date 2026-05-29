---
owner: platform-ops
status: consolidated
---

# Supply-Chain Risk Register

| Risk ID | Category | Description | Impact | Likelihood | Mitigation | Offline Compatibility | Determinism | Tenant Isolation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SCR-001 | Dependency Intake | Unreviewed dependency introduces hidden behavior or telemetry. | High | Medium | Review dependency purpose, pin versions, prefer vendoring or mirrors. | Required | Required | Required | Open |
| SCR-002 | Provenance Gap | Artifact origin cannot be reconstructed from repository records. | High | Medium | Record placeholder provenance metadata and retention rules. | Required | Required | Required | Open |
| SCR-003 | Reproducibility Drift | Builds cannot be repeated closely enough for governance review. | Medium | Medium | Pin inputs, document drift, compare artifacts during review. | Required | Required | Required | Open |
| SCR-004 | Cross-Tenant Leakage | Shared artifact cache exposes tenant-scoped metadata. | High | Low | Partition storage, sanitize logs, review visibility rules. | Required | Required | Required | Open |
| SCR-005 | Offline Packaging Failure | Critical dependency path assumes mandatory cloud access. | High | Medium | Maintain vendored or mirrored path and test disconnected workflows. | Required | Required | Required | Open |
