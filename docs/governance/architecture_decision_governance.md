---
owner: platform-ops
status: consolidated
---

# Architecture Decision Governance

## Purpose

This document defines how ADRs and RFCs work together for architecture governance while preserving offline compatibility, determinism, and tenant isolation.

## ADR and RFC Relationship

- RFCs govern cross-cutting decisions with platform-wide, security, compatibility, federation, or supply-chain impact.
- ADRs capture narrower implementation decisions inside an already accepted architectural direction.
- An ADR may reference an RFC as its governing context.
- An RFC may require one or more ADRs to capture bounded implementation choices.

## When to Use an ADR

Use an ADR when the change is local to one bounded area and does not redefine platform-level contracts, extension compatibility, federation behavior, or supply-chain policy.

## When to Use an RFC

Use an RFC when the change affects architecture boundaries, external or internal contracts, extension ABI, plugin governance, schema compatibility, replay semantics, federation interoperability, threat posture, or supply-chain governance.

## Required Review Escalations

- Require a threat model when a change alters trust boundaries, identity, receipts, sandboxing, attestation placeholders, plugin surfaces, or federation behavior.
- Require a compatibility review when a change alters schemas, ABI-like contracts, replay expectations, migration paths, deprecation windows, or version negotiation.
- Require a supply-chain review when a change introduces dependencies, vendored bundles, artifact provenance expectations, SBOM placeholders, build pipeline changes, or package distribution changes.

## Governance Expectations

- All accepted architectural decisions must document determinism impact.
- All accepted architectural decisions must document offline compatibility impact.
- All accepted architectural decisions must document tenant isolation impact.
- Rollback and migration expectations must be explicit.

## Decision Records

ADRs remain concise. RFCs remain comprehensive. Both must avoid unsupported claims and must not imply external approval, production PKI, or formal certification.
