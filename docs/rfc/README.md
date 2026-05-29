---
owner: platform-ops
status: consolidated
---

# RFC Repository

This repository defines the formal RFC workflow for architecture, governance, compatibility, federation, security, and supply-chain changes.

## Purpose

RFCs are required for cross-cutting changes that affect platform behavior, security posture, determinism, offline compatibility, tenant isolation, extension compatibility, federation contracts, or supply-chain controls.

## Status Model

Allowed RFC statuses:

- `draft`
- `proposed`
- `accepted`
- `rejected`
- `superseded`
- `deprecated`

## Required Sections

Every RFC must include:

- `Summary`
- `Context`
- `Goals`
- `Non-Goals`
- `Design`
- `Security Considerations`
- `Determinism Impact`
- `Offline Compatibility`
- `Tenant Isolation Impact`
- `Rollback Plan`

## File Naming

- `NNNN-short-kebab-case-title.md`
- Numbers are sequential and zero-padded to four digits.
- `0000-rfc-process.md` defines the repository process and is the process anchor.

## Workflow

1. Create a new RFC in `draft` status with all required sections.
2. Request architecture, security, compatibility, and supply-chain review as applicable.
3. Move to `proposed` once review comments are addressed.
4. Move to `accepted` only after explicit governance approval.
5. Use `rejected`, `superseded`, or `deprecated` to preserve historical traceability.

## Review Gates

- Threat modeling is required when an RFC changes trust boundaries, identity, federation, sandboxing, receipts, attestation placeholders, or supply-chain behavior.
- Compatibility review is required when an RFC changes ABI, schemas, capability negotiation, extension contracts, replay behavior, or federation interoperability.
- Supply-chain review is required when an RFC changes dependencies, build provenance, artifact distribution, vendoring strategy, or offline packaging.

## Initial RFCs

- `0000-rfc-process.md`
- `0001-extension-runtime-governance.md`
- `0002-sovereign-federation-governance.md`
