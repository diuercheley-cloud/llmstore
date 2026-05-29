---
owner: platform-ops
status: consolidated
---

# Plugin Security Model

## Principles

1. **Default-safe** — Every permission is denied by default. Plugins must declare permissions in the manifest; each requires explicit admin approval.
2. **Defence in depth** — Checksum verification, signature verification (optional but enforceable), permission allowlist/denylist, and sandbox execution boundaries compose to form overlapping controls.
3. **No arbitrary code execution** — Plugins run inside a controlled interface (`PluginContract`). The `PluginLoader` validates every load against the declared manifest.
4. **Audit trail** — Every install, enable, disable, upgrade, and uninstall produces a `SecurityEvent` and is recorded in the database.

## Verification Pipeline

```
Upload .zip/.tar.gz
    │
    ├─ 1. Extract manifest.json
    ├─ 2. Validate manifest v1 schema
    │      ├─ plugin_type ∈ PLUGIN_TYPES
    │      └─ permissions ⊆ ALLOWED_PERMISSIONS
    ├─ 3. Archive checksum verification (if checksums.archive present)
    ├─ 4. Allowlist / Denylist check
    ├─ 5. Signature verification (if PLUGIN_SIGNATURE_REQUIRED)
    │      └─ PKIService.verify_certificate(certificate_chain)
    └─ 6. Register in PluginRegistry (legacy sync)
```

## Signature Verification

When `PLUGIN_SIGNATURE_REQUIRED=true`:

- The manifest **must** contain a `signature` field.
- The manifest **should** contain a `certificate_chain` in PEM format.
- `PKIService.verify_certificate()` checks:
  - Certificate is not revoked (checked against database + CRL).
  - Certificate signature is valid against the root CA.
  - Certificate is not expired.
- If PKI is disabled (`PKI_ENABLED=false`), verification is advisory and logs a warning.

## Permission Model

| Layer | Mechanism |
|---|---|
| Manifest declaration | Plugin lists required permissions in `manifest.json` |
| Schema validation | `ManifestV1.validate_permissions()` rejects unknown permissions |
| Allowlist/Denylist | `_get_allowlist()` and `_get_denylist()` can be extended to check Redis or database |
| Admin approval | Each permission is stored with `granted=False` by default; admin must explicitly approve |
| Runtime enforcement | `PluginLoader.load_plugin()` checks permissions against `allowed_permissions` set |

## Trust Reports

Each plugin version can have an associated `PluginTrustReport`:
- `trust_score` (0.0–1.0) — overall trust assessment
- `vulnerabilities_found` — count of known vulnerabilities
- `is_signed` / `signer_identity` — code signing status
- `report_details` — arbitrary JSON from scanning tools (Trivy, Grype, etc.)

## Enable / Disable

- Plugins are installed **disabled** by default.
- Enabling a plugin toggles `is_enabled=true` and updates the legacy `PluginRegistry.is_active`.
- Disabled plugins are not loaded by `PluginLoader`.
- `uninstall` removes all permissions, the legacy registry entry, and the plugin files from disk.

## Upgrade / Downgrade

- Upgrading preserves `config_json` from the previous install.
- New permissions from the upgraded manifest are added with `granted=False`.
- The old version archive remains on disk until explicitly cleaned.

## Config Settings

| Variable | Default | Description |
|---|---|---|
| `PLUGIN_SIGNATURE_REQUIRED` | `false` | Require signature in manifest |
| `PKI_ENABLED` | `false` | Enable PKI certificate verification |
| `ATTESTATION_MODE` | `"advisory"` | Enforcing vs advisory mode for signature failures |

## Related

- [Manifest v1](manifest-v1.md)
- [Marketplace](marketplace.md)
- `app/contracts/plugin_types.py` — allowed permissions and plugin types
- `app/services/plugins/plugin_marketplace.py` — full lifecycle implementation
- `app/services/plugins/plugin_loader.py` — runtime loader with permission enforcement
