# Local Security Policy and Guidelines

This document outlines the security checks and guidelines for the local environment of the `llm-inference-stack`.

## CORS Policy (Local Appliance)

In `LOCAL_APPLIANCE_MODE`, the stack enforces a strict "deny-by-default" CORS policy:

- **Wildcard Prohibition**: `*` is not permitted as an origin.
- **Explicit Safelist**: Only origins listed in `CORS_ALLOW_ORIGINS` are accepted.
- **Loopback Defaults**: If no origins are configured, `localhost` and `127.0.0.1` are allowed by default for the configured `HOST_PORT`.
- **Validation**: Run `./scripts/validate-cors-local-appliance.sh` to confirm the active CORS policy.

## Running the Security Report
Before releasing, demonstrating, or validating local changes, run the security report to ensure no sensitive data is leaked or poorly configured:
```bash
make security-report
```
Or directly:
```bash
./scripts/security-report-local.sh --strict
```

## Abuse Protection Validation
To ensure the system remains stable under misuse or targeted abuse (invalid keys, floods, giant payloads), run the abuse protection suite:
```bash
make validate-abuse
```
This script validates:
- Authentication failures (invalid/revoked keys)
- Rate limiting and quotas (via safe probe with `readiness-rate-limit-test` plan)
- Payload size and complexity limits
- Multi-tenant isolation under abuse

## Interpreting the Score
The report returns a score based on its findings:
- **PASS**: All checks passed, were skipped, or findings were classified as safe (e.g., redacted artifacts). The environment is considered clean.
- **WARN**: Some non-critical findings were detected. Review the report in `artifacts/security-report/`.
- **FAIL**: Critical security issues or secret leaks detected. **Do not proceed with release.**
