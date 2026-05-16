# Extension Compatibility Policy

## Purpose

This policy defines how future plugins and extensions will be evaluated for compatibility without implementing runtime execution. It preserves offline compatibility, determinism, and tenant isolation as first-class governance constraints.

## Compatibility Scope

- plugin and extension manifest schemas
- ABI-like contract expectations
- capability declarations
- federation exchange metadata
- receipts and attestation placeholder metadata

## ABI Compatibility

ABI compatibility means a consumer can interpret extension contract fields, lifecycle states, and capability descriptors without undefined behavior. Breaking ABI changes require RFC review and may trigger blocking.

## Capability Boundaries

Capabilities must be explicit, minimal, and deny-by-default. A compatibility claim is invalid if a manifest requests capabilities outside documented boundaries or relies on hidden privileges.

## Schema Compatibility

- Additive optional fields may be `MINOR`.
- Removed or retyped required fields are breaking.
- Unknown fields must be ignored or rejected according to the contract version, and that behavior must be documented.

## Federation Compatibility

Federation metadata for extensions must preserve offline compatibility, deterministic interpretation, and tenant isolation across peer exchanges. Mixed-version federation must declare acceptance, warning, or blocking outcomes.

## Blocking Criteria

Compatibility review must block an extension or plugin proposal when:

- required schema fields are missing or ambiguous
- capabilities exceed policy boundaries
- replay interpretation is not deterministic
- tenant isolation assumptions are undefined
- federation behavior is incompatible
- rollback behavior is missing
