---
owner: platform-ops
status: consolidated
---

# Sovereign AI Guardrails + Air-Gapped Governance

Phase 37 adds sovereign governance controls for offline and air-gapped environments.

## Scope

- Airgap governance bundles with signed manifests
- Offline CRL handling for keys, bundles, peers, and encrypted exports
- Chain-of-custody recording for physical transfer workflows
- Sovereign export restrictions for `sovereign_restricted` data
- Hardware attestation placeholder records for report-first enforcement

## Airgap Packages

Airgap packages are created in `commercial_airgap_sync_packages` and exported as a logical bundle containing:

- `manifest.json`
- `payload.json` or `payload.enc`
- `signature.txt`
- `checksums.txt`
- `chain_of_custody.json`

Package types:

- `policy_bundle`
- `audit_trail`
- `evidence`
- `crl`
- `full_governance_snapshot`

The manifest is hashed and signed offline. For sovereign content the package must be encrypted, signed, and backed by chain-of-custody metadata.

## Offline CRL

Offline revocation lists are stored in `commercial_offline_revocation_lists`.

Supported revocation scopes:

- tenant encryption key fingerprints
- policy bundle hashes
- governance federation peer ids
- exported airgap package hashes

Applying a CRL revokes matching tenant keys, deprecates matching bundles, disables matching peers, and rejects matching airgap packages.

## Chain Of Custody

Every airgap package requires `chain_of_custody_json.events`.

Each event should include:

- `actor`
- `action`
- `timestamp`
- optional transfer metadata such as media id or seal id

This is intentionally sanitized before persistence. Secrets and raw credentials must not be placed in the chain payload.

## Sovereign Restricted Data

`sovereign_restricted` is a hard export class.

Rules:

- cannot be exported via online governance federation
- can only leave the cluster through encrypted airgap packages
- requires a signed manifest
- requires chain-of-custody metadata

This phase implements guardrails and blocking behavior. It does not promise formal confidential computing.

## Hardware Attestation Placeholder

Hardware attestation is a secure placeholder flow in `commercial_hardware_attestation_records`.

Supported record types:

- `tpm`
- `secure_boot`
- `sgx`
- `sev`
- `placeholder`

Current phase behavior:

- stores sanitized evidence
- computes evidence hash
- supports verify and summary flows
- can block enforcement when status is `untrusted` and mode is `enforce`

No real TPM/SGX/SEV dependency is required in this phase.

## Admin Endpoints

- `GET /admin/governance/airgap/packages`
- `POST /admin/governance/airgap/packages`
- `POST /admin/governance/airgap/packages/{id}/export`
- `POST /admin/governance/airgap/packages/import`
- `POST /admin/governance/airgap/packages/{id}/verify`
- `POST /admin/governance/airgap/packages/{id}/reject`
- `GET /admin/security/offline-crl`
- `POST /admin/security/offline-crl`
- `POST /admin/security/offline-crl/{id}/apply`
- `GET /admin/security/hardware-attestation`
- `POST /admin/security/hardware-attestation/collect`
- `POST /admin/security/hardware-attestation/verify`

## Limitations

- no physical media automation is performed by the product
- no real TPM/SGX/SEV attestation is performed
- no SaaS dependency is introduced
- no plaintext secret export is allowed by this phase
- no formal confidential computing guarantee is claimed
