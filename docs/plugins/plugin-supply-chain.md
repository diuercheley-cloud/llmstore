# Plugin Supply Chain

## Surface Status

- `GET /admin/operations/plugin-supply-chain/provenance`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance`: `beta`
- `GET /admin/operations/plugin-supply-chain/provenance/{provenance_id}`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/verify`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/revoke`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/sbom`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/dependency-verify`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/lineage`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/replay-verify`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/receipt`: `beta`
- `GET /admin/operations/plugin-supply-chain/sbom`: `beta`
- `GET /admin/operations/plugin-supply-chain/dependency-verifications`: `beta`
- `GET /admin/operations/plugin-supply-chain/lineage`: `beta`
- `GET /admin/operations/plugin-supply-chain/receipts`: `beta`
- `GET /admin/operations/plugin-supply-chain/dashboard`: `beta`
- `POST /admin/operations/plugin-supply-chain/provenance/{provenance_id}/sign-placeholder`: `simulated`

## Security Model
Plugins extend the platform's core capabilities and must adhere to strict supply chain security standards.

- **Mandatory Manifests**: Every plugin must include a JSON manifest defining its version, entrypoint, and required permissions.
- **Permission Boundaries**: Plugins are restricted to a whitelist of allowed permissions (`read_data`, `write_data`, `network_out`, `execute_sandbox`). Any attempt to request broader access results in a load error.
- **Audit Trails**: Installation and activation of plugins generate security events in the audit log.
- **Compatibility Matrix**: Verification ensures that plugins are compatible with the current platform version.
- **Cryptographic Provenance**: Signatures ensure that the plugin originates from a trusted author and has not been tampered with in transit.

The `sign-placeholder` endpoint is intentionally non-production. It generates deterministic placeholder signature records for workflow testing and audit chaining. Real provenance, dependency verification, SBOM generation, lineage, replay verification, and receipt APIs remain `beta` because they are functional but still evolving.
