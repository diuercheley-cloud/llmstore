---
owner: platform-ops
status: consolidated
---

## Official Bounded Contexts

`core_runtime`
- deterministic runtime abstractions, local execution readiness boundaries, governed runtime coordination

`governance`
- deterministic policy, approvals, governance review state, compliance decisions

`federation`
- offline-first federation contracts and deterministic exchange boundaries

`plugin_runtime`
- deterministic plugin contract, compatibility, isolation, load-plan governance, and bounded local sandboxed plugin execution

`supply_chain`
- provenance, artifact lineage, reproducibility and integrity governance

`operations`
- deterministic operational workflows, events, recovery planning

`security`
- trust boundaries, local PKI, attestation policy, isolation rules, and no hardware-backed trust guarantee by default

`financial`
- billing and finance-specific governance contracts

`sovereign`
- airgap, locality, tenant sovereignty, export and deployment constraints

`observability`
- local metrics, traces, timelines, sanitized operational visibility

`data_governance`
- data zoning, lineage, retention, export controls

`disaster_recovery`
- backup manifests, replay verification, dry-run recovery governance
