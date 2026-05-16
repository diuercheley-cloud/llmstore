# Phase 75: Adapter Promotion Workflow

## Overview
Phase 75 implements a deterministic and gated workflow for promoting adapters between stages. This phase ensures that adapters move from draft to production eligibility through a series of verifiable checks (gates) and simulations, without ever executing real code or infrastructure commands.

## Promotion Lifecycle
Adapters move through the following stages:
1.  **draft**: Initial registration.
2.  **sandboxed**: Passed basic sandbox validation.
3.  **registry_approved**: Approved in the Signed Adapter Registry.
4.  **staging_simulated**: Successfully simulated in a staging-like environment (deterministic).
5.  **production_eligible**: Marked as safe for operational use.

## Promotion Gates
Every promotion requires passing specific gates:
- `registry_entry_exists`: Entry must be in the registry.
- `registry_entry_approved`: Entry must be approved for staging/production targets.
- `not_revoked`: Entry must not be revoked.
- `not_blocklisted`: Entry must not be on a blocklist.
- `sandbox_manifest_valid`: Manifest must be structurally sound.
- `sandbox_simulation_passed`: Previous sandbox runs must have succeeded.
- `no_policy_violations`: No active policy violations for the adapter.
- `staging_simulation_required`: Staging simulation is mandatory for production.
- `approval_required_for_production_eligible`: Explicit admin approval for final stage.
- `signature_placeholder_present`: Must have a verifiable (placeholder) signature.

## Determinism & Security
- **No Real Execution**: Adapters are never executed. Promotion only changes their "eligibility" status.
- **Offline-First**: All gate evaluations and hashing are performed locally.
- **Verifiable Receipts**: Every promotion action generates a receipt with a signature placeholder.
- **Tenant Isolation**: All promotion data is strictly scoped by `client_id`.

## Rollback (Depromotion)
Promotions can be rolled back to a previous stage. Rollbacks are audit events and require a mandatory reason.
