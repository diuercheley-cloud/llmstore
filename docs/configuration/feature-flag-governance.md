# Feature Flag Governance

This document describes the policies, schema, and tools for feature flag governance in the `llm-inference-stack`.

## Objectives

To stabilize the system and ensure rigorous production safety, all feature flags are registered, tracked, and validated. This prevents:
- **Configuration Drift**: Feature flags existing in settings/environments but not officially documented.
- **Orphaned Flags**: Dead code flags remaining in the codebase after features are stabilized or retired.
- **Unmanaged Risk**: High-risk feature flags enabled by default or experimental flags lacking an owner.

---

## Policies

1. **Owner Rule**: Every feature flag must have a declared `owner` (person or team) responsible for its lifecycle.
2. **Safe Defaults**:
   - Any flag classified with `risk_level: high` **must** default to `false`.
   - Any flag classified with `status: experimental` **must** be opt-in (default to `false`).
3. **Deprecation Path**: Any flag with `status: deprecated` **must** declare a `remove_after` date or a `replacement` flag.
4. **No Unregistered Flags**: Any boolean setting added to the codebase or configuration **must** be registered in the YAML registry.

---

## YAML Registry Schema (`config/feature-flags.yaml`)

All flags are defined in `config/feature-flags.yaml` under the following structure:

```yaml
- name: FEATURE_FLAG_NAME
  default: false                      # Default value (boolean)
  owner: platform-ops                 # Responsible owner
  area: Billing                       # System area (e.g., Billing, RAG, etc.)
  status: active                      # active | deprecated | experimental | internal
  introduced_in: v1.9.0               # First version where it appeared
  risk_level: low                     # low | medium | high
  dependencies: []                    # Pre-requisite feature flags
  conflicts: []                       # Mutually exclusive feature flags
  safe_default_reason: "Explanation"  # Rationale for the default value
```

---

## Command Line Interface (CLI)

Feature flag integrity is validated via a shell script integrated into `make validate`, `make stabilization-check`, and `release-gate.sh`.

### Commands

To run validation:
```bash
./scripts/validators/check-feature-flags.sh
```

Or via Makefile:
```bash
make validate-feature-flags
```

### Checks Performed
1. **Registry Policy Checks**: Validates schema, owner presence, experimental opt-in, high-risk defaults, and deprecated replacement rules.
2. **Missing Registration Scan**: Compares registry against settings in `control_plane/app/core/config.py` and `.env.example`. Any unregistered boolean setting fails the build.
3. **Orphans Scan**: Detects and reports registered flags that are no longer referenced in Python code or configuration.

---

## API Endpoints

Admin endpoints are exposed under `/admin/feature-flags` and require admin authentication:

- `GET /admin/feature-flags`: List all registered feature flags.
- `GET /admin/feature-flags/deprecated`: List all deprecated feature flags.
- `GET /admin/feature-flags/conflicts`: Find active conflicts where mutually exclusive flags are enabled simultaneously in the running environment.
- `POST /admin/feature-flags/validate`: Validate the feature flag registry against policy rules and return detailed violations.
- `GET /admin/feature-flags/{name}`: Retrieve metadata for a specific feature flag.
