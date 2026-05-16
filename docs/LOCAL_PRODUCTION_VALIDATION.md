# Local Production Validation

This document describes the final validation suite for the local production stack exposed through `http://localhost`.

## Command

Run the full suite with:

```bash
make validate-local-production
```

For architecture-only validation without external services, use:

```bash
make validate-platform-architecture
```

The Makefile target runs:

```bash
./scripts/validate-local-production-full.sh
```

## Scope

The suite validates the local stack only. Real PSP integration is not part of this scope, so missing PSP credentials are reported as a warning and do not fail the run. Billing validation uses manual invoice and payment flows.

LM Studio is optional. If the LM Studio endpoint is offline, `validate-lmstudio-backend.sh` is marked as skipped with a warning. This does not fail the run.

RAG validation is conditional. If `RAG_ENABLED=true`, the multi-client RAG validation runs as a critical test. If RAG is disabled, it is skipped with a warning.

## Execution Order

The full suite executes these validations in order:

1. `validate-localhost-mode.sh`
2. `validate-status-local.sh`
3. `validate-admin-lab-local.sh`
4. `validate-lmstudio-backend.sh`, skipped when LM Studio is offline
5. `validate-routing-local.sh`
6. `validate-plan-queues.sh`
7. `validate-client-portal-local.sh`
8. `validate-api-keys-local.sh`
9. `validate-rag-local-multiclient.sh`, only when RAG is enabled
10. `validate-local-billing.sh`
11. `validate-local-docs.sh`
12. `validate-observability-local.sh`

## Reports

Every run creates an artifact directory:

```text
artifacts/local-production-validation/<timestamp>/
```

The directory contains:

- `summary.json`: machine-readable validation report
- `summary.md`: human-readable validation report
- `<script>.log`: stdout and stderr for each executed or skipped validation script

The summaries include:

- version
- git commit
- base URL
- services tested
- endpoints tested
- scripts executed
- failures
- warnings
- duration
- next steps

## Exit Codes

- `0`: all critical tests passed
- non-zero: one or more critical tests failed

Warnings and skips do not cause a non-zero exit code unless a critical validation also fails.

## Troubleshooting

Open the generated `summary.md` first, then inspect the individual script logs listed in the `Scripts Executed` table.

Common local issues:

- Stack is not running: check `docker compose ps`.
- The configured `HOST_PORT` does not match the service exposed on localhost.
- `ADMIN_TOKEN` in the environment does not match the running control plane.
- RAG worker is disabled or not processing documents while `RAG_ENABLED=true`.
- LM Studio is offline, which should appear only as a warning or skipped validation.
