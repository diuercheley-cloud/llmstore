---
owner: platform-ops
status: consolidated
---

# Supported Surface Areas & Lifecycle Policies

This document defines the platform capabilities, surface area boundaries, and lifecycle classifications.

## Lifecycle Classifications

All APIs, UI pages, services, scripts, feature flags, adapters, dashboards, and tests are classified into one of the following lifecycle stages:

| Classification | Description | Support Level |
| :--- | :--- | :--- |
| **supported** | Fully operational and supported capability with high test coverage and documentation. | Production |
| **beta** | Functional but subject to rapid evolutionary changes. Safe for pilot deployments. | Pilot |
| **experimental** | Proof of concept or development-only capabilities. Disabled by default. | Development |
| **deprecated** | Legacy features scheduled for deletion. Accessing deprecated APIs triggers warning headers. | Deprecated |
| **internal** | System-internal endpoints requiring RBAC/admin auth, not listed as public APIs. | Operator-only |
| **internal_only** | System-internal code, test utilities, or pipeline scripts. | Operator-only |
| **removed_candidate** | Dead endpoints removed from active registry. | None (Scheduled for deletion) |
| **orphaned** | Dead code, unreferenced endpoints, unrouted pages, or unused scripts. | None (Scheduled for deletion) |

---

## Core Capabilities Mapping

For a structured view of all official platform capabilities, refer to the configuration file:
- [supported-surface.yaml](file:///home/kleber/llm-inference-stack/config/supported-surface.yaml)

---

## Orphaned Code Remediation

If a component is audited and marked as `orphaned`, the following steps must be taken:
1. **Remove**: Delete the unused script, page, or service.
2. **Classify**: If the component must remain but is not fully supported, explicitly mark it as `deprecated` or `internal_only` in the corresponding YAML configurations.
