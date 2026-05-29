# Plugin Supply Chain

## Security Model
Plugins extend the platform's core capabilities and must adhere to strict supply chain security standards.

- **Mandatory Manifests**: Every plugin must include a JSON manifest defining its version, entrypoint, and required permissions.
- **Permission Boundaries**: Plugins are restricted to a whitelist of allowed permissions (`read_data`, `write_data`, `network_out`, `execute_sandbox`). Any attempt to request broader access results in a load error.
- **Audit Trails**: Installation and activation of plugins generate security events in the audit log.
- **Compatibility Matrix**: Verification ensures that plugins are compatible with the current platform version.
- **Cryptographic Provenance**: Signatures ensure that the plugin originates from a trusted author and has not been tampered with in transit.
