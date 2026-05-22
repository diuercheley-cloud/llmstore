# Security: v1.10.0-agentic-runtime

## Status

- `make security`: `PASS_WITH_WARNINGS`
- `bash scripts/check-secrets.sh --all`: `PASS`
- `scripts/check-alembic-integrity.sh`: `PASS`

## Guardrails Confirmed

- Agent execution disabled by default
- Tool execution disabled by default
- Destructive tools disabled by default
- Memory disabled by default
- Human approval enabled for high-risk actions
- Supported surface remains beta/experimental
- Raw prompt exposure is out of policy by default
- Cross-tenant memory is out of scope

## Warnings

- Ignored/generated backup artifacts still contain test secret-like values and are reported as non-blocking warnings.
- The security report also reports legacy non-executable shell scripts as warnings.
