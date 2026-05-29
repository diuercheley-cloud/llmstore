---
owner: platform-ops
status: consolidated
---

# Operational Guide: Signed Adapter Registry

## Introduction
The Signed Adapter Registry provides a governed lifecycle for remediation adapters. It ensures that only validated, compliant, and approved adapter manifests can be registered and used in the system.

## Lifecycle Statuses
1.  **Draft:** Initial state upon registration. Not eligible for approval yet.
2.  **Submitted:** Ready for administrative review.
3.  **Approved:** Verified and permitted for use (subject to policies).
4.  **Rejected:** Administrative decision to deny the manifest.
5.  **Revoked:** Previously approved manifest that is now prohibited.
6.  **Blocked:** Prohibited by blocklist. Always takes precedence.
7.  **Deprecated:** Older version that should be phased out.

## Policy Enforcement
The registry policy engine enforces hard constraints on all manifests:
- `sandbox_required` must be `True`.
- `dry_run_default` must be `True`.
- `network_access_allowed` must be `False`.
- `subprocess_allowed` must be `False`.
- `external_system_access_allowed` must be `False`.

Any manifest failing these checks will be rejected at the registration stage.

## Allowlist and Blocklist
- **Allowlist:** Explicitly permits specific manifest hashes even if they haven't gone through the full standard lifecycle (e.g., pre-approved system adapters).
- **Blocklist:** Explicitly prohibits specific manifest hashes. This is the ultimate authority; a blocked manifest cannot be approved or used even if it appears in an allowlist.

## Receipts and Audit
Every significant registry action (registration, status change, policy update) generates a `RegistryReceipt` and an `Audit Event`. These receipts use deterministic `signature_placeholders` to facilitate future integration with real PKI.

## Limitations
- **No Real Execution:** Adapters registered here cannot be executed. This is a metadata and governance registry only.
- **Placeholder Signatures:** Signatures are not cryptographically secure and are for workflow validation purposes only.
- **Offline Integrity:** All checks are local. The system does not verify hashes against external authorities.
