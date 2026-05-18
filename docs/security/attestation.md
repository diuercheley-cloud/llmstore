# Node Attestation

The system provides verifiable attestation reports to ensure the integrity of the running node.

## Attestation Measurements

Reports include:
- **Binary Hash**: Hash of the core application code.
- **Config Hash**: Deterministic hash of non-sensitive configuration settings.
- **Migrations**: Status of applied database migrations.
- **Plugins**: Checksums of all active plugins.
- **Hardware Trust**: Measurements from the Hardware Trust Provider (e.g., TPM).

## Attestation Modes

- **Advisory (Default)**: Reports are generated and logged, but failures do not block operations.
- **Enforcing**: Failures in attestation block the node's readiness and prevent invalid plugins from loading.

## Endpoints

- `GET /admin/security/attestation/report`: Generate a new signed attestation report.
- `POST /admin/security/attestation/verify`: Verify an existing attestation report.
