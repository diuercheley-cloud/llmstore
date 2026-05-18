# Plugin Runtime Security

The plugin system enforces strict security controls on loaded extensions.

## Validation Process

1. **Manifest Validation**: Name, version, and entrypoint must be present.
2. **Permission Check**: Only allowed permissions (e.g., `read_data`, `network_out`) can be requested.
3. **Checksum Verification**: The plugin binary must match the `sha256` in the manifest.
4. **Signature Verification**: If `PLUGIN_SIGNATURE_REQUIRED=true`, the plugin must be signed by a trusted certificate.

## Enforcement

In `enforcing` mode, any validation failure prevents the plugin from being registered or loaded. In `advisory` mode, failures are logged as `security_event` but the plugin is still allowed to load.
