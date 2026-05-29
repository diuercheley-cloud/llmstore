---
owner: platform-ops
status: consolidated
---

# Plugin Certification Workflow Placeholder

## Purpose

This document defines a placeholder-only workflow for future plugin review records. It exists to organize governance metadata while preserving offline compatibility, determinism, and tenant isolation. It is not a real certification.

## Statuses

- `submitted`
- `sandbox_reviewed`
- `compatibility_checked`
- `security_reviewed`
- `placeholder_certified`
- `rejected`
- `revoked`

## Workflow

1. `submitted`: metadata package is received for documentation review.
2. `sandbox_reviewed`: declared sandbox assumptions are checked against policy placeholders.
3. `compatibility_checked`: manifest, schema, capability, rollback, and replay notes are reviewed.
4. `security_reviewed`: threat model and supply-chain notes are reviewed.
5. `placeholder_certified`: repository-level placeholder record may be issued.
6. `rejected`: proposal is denied.
7. `revoked`: a previously issued placeholder record is withdrawn.

## Explicit Limits

- This workflow is `placeholder-only`.
- `placeholder_certified` is an internal documentation status, not a real certification.
- No production PKI is implemented here.
- No governmental approval, regulatory approval, or formal third-party certification is implied.
- No runtime execution approval is granted by this document.

## Review Inputs

- threat model
- compatibility review
- supply-chain review
- rollback notes
- offline compatibility notes
- determinism notes
- tenant isolation notes

## Blocking Conditions

- missing threat model when required
- missing compatibility declaration
- undefined tenant isolation boundary
- incompatible offline packaging assumptions
- unsupported capability escalation

## Record Retention

Placeholder review records must remain interpretable for replay and audit purposes, but they do not represent a trust guarantee or external approval.
