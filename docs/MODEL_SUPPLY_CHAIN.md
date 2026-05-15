# Model Supply Chain

Phase 38 adds an internal, auditable model supply chain for local and API-backed models. This is not a formal third-party supply-chain attestation system. It implements internal controls for signed manifests, provenance capture, checksum verification, quarantine and offline promotion.

## Signed Registry

The signed model registry stores:

- model identity and alias
- optional local artifact path for admin-only workflows
- model format
- SHA-256 checksum or `manifest-only` for API-provider models
- manifest hash
- optional internal signature
- trust state: `trusted`, `pending`, `untrusted`, `quarantined`, `revoked`
- tenant scope
- approval metadata

Local artifacts should provide a checksum. API-provider entries may operate without a local file and use `manifest-only`.

## Trust and Approval

Trust states are enforced through:

- `COMMERCIAL_MODEL_SUPPLY_CHAIN_ENABLED`
- `COMMERCIAL_MODEL_TRUST_ENFORCEMENT_MODE=disabled|report_only|enforce`
- `COMMERCIAL_MODEL_REQUIRE_TRUSTED_FOR_ROUTING`
- `COMMERCIAL_MODEL_REQUIRE_CHECKSUM_FOR_LOCAL`
- `COMMERCIAL_MODEL_QUARANTINE_ON_CHECKSUM_MISMATCH`

Behavior:

- `disabled`: no supply-chain enforcement
- `report_only`: trust issues are visible but existing routing remains available
- `enforce`: non-trusted models are blocked from selection/routing

When a local file checksum no longer matches the registered digest, the registry entry can be moved to `quarantined` and an audit event is written.

## Provenance

Provenance attestations capture:

- source type: local file, vendor, air-gap, manual, API provider
- source URI when safe to retain
- source cluster for federation and air-gap workflows
- import method
- artifact hash
- sanitized evidence payload
- optional chain-of-custody

This integrates with existing air-gap governance and offline CRL controls. No automatic model download is performed.

## Offline Promotion Bundles

Promotion bundles support transferring model approval metadata across disconnected environments. A bundle carries:

- model manifest
- checksum
- provenance summary
- optional signature
- chain-of-custody

Bundle states:

- `created`
- `verified`
- `promoted`
- `rejected`
- `expired`

Promotion creates a new pending registry entry on the target side so approval remains explicit and auditable.

## Revocation and Quarantine

Revocation records track:

- checksum mismatches
- policy violations
- security risks
- manual operator actions
- CRL-driven invalidation

Offline CRL application can revoke models by:

- model checksum
- manifest hash
- registry entry id
- source peer through provenance linkage

Revoked or quarantined entries are blocked when enforcement is active.

## Admin and Portal Visibility

Admin APIs expose:

- signed registry entries
- provenance records
- promotion bundles
- trust summary and enforcement mode

Portal visibility is tenant-scoped and excludes sensitive internals such as absolute filesystem paths or provider secrets.

## Limitations

- No formal external supply-chain attestation is claimed
- Signatures are internal integrity controls, not a public PKI workflow
- No automatic fetch from Hugging Face or vendor sources
- Tenant views do not expose internal file paths or provider secrets
