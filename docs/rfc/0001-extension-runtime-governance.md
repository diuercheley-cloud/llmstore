---
owner: platform-ops
status: consolidated
---

# RFC 0001: Extension Runtime Governance

## Status

draft

## Summary

Define governance constraints for a future extension and plugin runtime before runtime execution is implemented.

## Context

Phase 79 and later work may expand extension capabilities. Governance must be established before runtime execution exists so that compatibility, sandboxing, review gates, and placeholder certification wording are fixed in advance. The repository also needs clear limits for offline compatibility, determinism, and tenant isolation.

## Goals

- Define approval expectations for future extension runtime changes.
- Establish compatibility and capability boundaries before execution exists.
- Require threat modeling for sandbox and plugin trust boundaries.
- Keep extension governance compatible with sovereign offline deployment.

## Non-Goals

- Implement plugin runtime execution.
- Execute extensions.
- Create real certification, signatures, or production PKI.
- Promise external compliance or approval.

## Design

Future extension runtime work must use an RFC when it changes:

- executable plugin lifecycle
- extension ABI or schema contracts
- capability negotiation or privilege boundaries
- federation exchange of extension metadata
- receipts or attestation placeholders
- dependency provenance or distribution channels

ADRs may capture local implementation choices within an accepted RFC envelope. Compatibility review is mandatory for ABI, schema, replay, and federation changes. Threat modeling is mandatory for sandbox, privilege, receipt, and trust-boundary changes. Supply-chain review is mandatory for new dependencies, packaged artifacts, vendored bundles, or provenance metadata.

## Security Considerations

Threats include malicious manifests, sandbox escape attempts, capability escalation, forged compatibility claims, receipt tampering, and supply-chain contamination. Placeholder certification cannot be used as a security guarantee.

## Determinism Impact

Extension contracts must specify deterministic behavior expectations, replay compatibility requirements, and where side effects are forbidden or version-gated.

## Offline Compatibility

Extension governance must support offline compatibility, including local review, vendored dependency expectations, and no mandatory SaaS or cloud control plane for approval or operation.

## Tenant Isolation Impact

Extension governance must preserve tenant isolation through explicit storage boundaries, capability scoping, receipt partitioning, and blocked cross-tenant artifact reuse unless formally designed and reviewed.

## Rollback Plan

If a proposed extension governance model causes risk, revert to documented non-executable metadata-only handling, freeze new approvals, and preserve compatibility records for audit and replay review.
