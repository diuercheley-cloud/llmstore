---
owner: platform-ops
status: consolidated
---

# RFC 0000: RFC Process

## Status

accepted

## Summary

Define the standard process for proposing, reviewing, approving, rejecting, superseding, and deprecating formal RFCs.

## Context

The repository needs a stable governance process before later phases introduce broader runtime, extension, federation, and trust changes. The process must preserve determinism, offline compatibility, and tenant isolation in architectural decision making.

## Goals

- Standardize RFC lifecycle states and review gates.
- Require comparable structure across decisions.
- Make security, rollback, replay, and compatibility impacts explicit.
- Keep governance usable in offline and sovereign deployments.

## Non-Goals

- Implement code ownership automation.
- Replace ADRs for local implementation choices.
- Create legal approval or external certification workflows.

## Design

Allowed statuses are `draft`, `proposed`, `accepted`, `rejected`, `superseded`, and `deprecated`.

Each RFC must contain the required repository sections. New RFCs start as `draft`. Authors move an RFC to `proposed` after initial review readiness. Governance owners may mark an RFC `accepted` after required reviews are complete. Historical outcomes remain visible through `rejected`, `superseded`, and `deprecated`.

Required reviews:

- Threat model review for security-sensitive or trust-boundary changes.
- Compatibility review for ABI, schema, extension, replay, or federation changes.
- Supply-chain review for dependency, artifact, provenance, build, or packaging changes.

## Security Considerations

The process forces early treatment of spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, and supply-chain risk. RFCs that touch plugin or extension surfaces must declare sandbox assumptions and trust boundaries.

## Determinism Impact

Every RFC must explain whether behavior remains deterministic, where nondeterminism could enter, and how replay compatibility is preserved or intentionally version-gated.

## Offline Compatibility

Every RFC must explain how the change behaves in offline compatibility scenarios, including sovereign and air-gapped deployments with no mandatory SaaS or cloud dependencies.

## Tenant Isolation Impact

Every RFC must explain tenant isolation impact, including state separation, metadata exposure, audit boundaries, and cross-tenant rollback or replay risks.

## Rollback Plan

Every RFC must define a rollback path, including deactivation steps, fallback behavior, migration reversal expectations, and how previously emitted artifacts remain interpretable.
