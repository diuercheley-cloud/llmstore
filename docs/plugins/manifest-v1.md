---
owner: platform-ops
status: consolidated
---

# Manifest v1 — Plugin Package Manifest

Every plugin distributed through the marketplace must include a `manifest.json` at the root of the archive.

## Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `manifest_version` | string | yes | Must be `"1"` |
| `name` | string | yes | Lowercase alphanumeric + `_` / `-`, 1–255 chars |
| `version` | string | yes | Semantic version (`MAJOR.MINOR.PATCH`) |
| `description` | string | no | Human-readable description |
| `author` | string | no | Author or organisation name |
| `license` | string | no | SPDX identifier or free text; default `"Proprietary"` |
| `entrypoint` | string | yes | Relative path to the plugin entrypoint file |
| `plugin_type` | string | yes | See [Plugin Types](#plugin-types) |
| `permissions` | list[string] | yes | Declared [Permissions](#permissions) |
| `checksums` | object | no | Map of filename → SHA-256 hex; key `"archive"` = archive checksum |
| `signature` | string | no | Base-64-encoded signature over canonical manifest JSON |
| `certificate_chain` | string | no | PEM certificate chain for signature verification |
| `minimum_platform_version` | string | no | Minimum platform version requirement; default `"1.0.0"` |
| `compatibility` | object | no | Key-value pairs for compatibility metadata |

## Plugin Types

| Type | Description |
|---|---|
| `provider_adapter` | Adapts an external LLM / inference provider |
| `billing_adapter` | Integrates a billing gateway or metering system |
| `rag_processor` | Custom RAG chunking, embedding, or retrieval logic |
| `observability_exporter` | Exports telemetry to an external observability backend |
| `auth_provider` | Custom authentication / SSO provider |
| `compliance_policy` | Regulatory or organisational compliance rule engine |
| `ui_extension` | Adds a custom panel/button to the admin frontend |

## Permissions

| Permission | Description |
|---|---|
| `read_data` | Read inference request/response data |
| `write_data` | Write inference request/response data |
| `network_out` | Make outbound network requests |
| `execute_sandbox` | Execute code within the sandbox |
| `read_config` | Read system configuration |
| `write_config` | Write system configuration |
| `read_logs` | Read system logs |
| `write_logs` | Write system logs |
| `read_metrics` | Read system metrics |
| `write_metrics` | Write system metrics |
| `access_secrets` | Access secret/credential storage |
| `access_audit` | Access audit trail |

## Example

```json
{
  "manifest_version": "1",
  "name": "my-custom-provider",
  "version": "1.2.0",
  "description": "Integrates with MyCustomLLM API",
  "author": "ACME Corp",
  "license": "MIT",
  "entrypoint": "plugin.py",
  "plugin_type": "provider_adapter",
  "permissions": ["network_out", "read_data"],
  "checksums": {
    "archive": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "signature": "MEYCIQ...",
  "certificate_chain": "-----BEGIN CERTIFICATE-----\n...",
  "minimum_platform_version": "1.9.0",
  "compatibility": {
    "python": [">=3.11"],
    "platform": [">=linux-x86_64"]
  }
}
```
