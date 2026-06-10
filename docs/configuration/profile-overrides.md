# Profile Overrides and Conflict Detection

While operational profiles provide a standard baseline, operators can override individual feature flags when necessary.

## Overrides
Any environment variable that matches a feature flag name will override the value defined in the profile.
Example:
```bash
export AGENT_RUNTIME_ENABLED=true
```

## Conflict Detection
The `ProfileResolver` automatically detects invalid combinations of flags. For example, requiring a MicroVM (`AGENT_CODE_SANDBOX_MICROVM_REQUIRED=true`) while setting the provider to `docker` will trigger a conflict warning.

## Auditing
Use the `scripts/validators/validate-platform-profile.sh` script to audit the current configuration:
```bash
./scripts/validators/validate-platform-profile.sh agentic-production
```
This will list the resolved flags, active overrides, and any detected conflicts.
