# Local Security Policy and Guidelines

This document outlines the security checks and guidelines for the local environment of the `llm-inference-stack`.

## Running the Security Report
Before releasing, demonstrating, or validating local changes, run the security report to ensure no sensitive data is leaked or poorly configured:
```bash
make security-report
```
Or directly:
```bash
./scripts/security-report-local.sh --strict
```

## Interpreting the Score
The report returns a score based on its findings:
- **PASS**: All checks passed or were skipped. The environment is considered clean.
- **PASS_WITH_WARNINGS**: Issues were found that might be risky (like open permissions or missing admin tokens in offline mode) but aren't critical failures. Review the warnings and fix if applicable.
- **FAIL**: Critical issues were detected (like checked-in secrets, unmasked API keys in logs, or globally exposed databases). You MUST fix these before proceeding. When running with `--strict`, high severity issues also result in FAIL.

## Common Warnings and Fixes
- **Unrestricted `.env.local` permissions**: Fix with `chmod 600 .env.local`.
- **Non-executable scripts**: Fix with `chmod +x scripts/*.sh`.
- **Exposed Database Ports**: Ensure your `docker-compose.yml` binds ports strictly to localhost (e.g., `127.0.0.1:5432:5432`).

## What NEVER to Commit
Do not commit the following to the repository:
- `.env`, `.env.local`
- Files within `.local/`
- Downloaded models (`models/`, `*.gguf`)
- User uploaded RAG data (`data/rag_uploads/`)
- Backups and Exports (`backups/`, `exports/`)

## Secrets Policy
- Run `make check-secrets` locally to detect leaked tokens.
- We never check in production or high-privileged API keys.
- Hash or mask API keys in logs.

## Logs and Artifacts Policy
- Logs must not contain full `POSTGRES_PASSWORD`, `REDIS_URL`, or `ADMIN_TOKEN`.
- Release manifests and test summaries must not export secrets.

## Admin Token
- The `ADMIN_TOKEN` should be strong and protected. Default or weak admin tokens will generate warnings in the security report.
- Ensure the Admin API endpoints enforce token-based authentication.

## API Keys
- Invalid API keys should return a HTTP `401 Unauthorized`.
- Revoked keys should be immediately blocked.

## RAG and TTS Local Data
- Local uploads for RAG and generated TTS audio files must be kept out of version control.
- Ensure you have safe cleanup procedures for this data when resetting environments.
- Use `./scripts/retention-local.sh` to apply the project's retention policy and safely remove temporary data.

## Secure Client Deletion and PII Removal
To comply with data protection standards even in local development:
- Use `scripts/delete-client-local.sh` for full offboarding.
- Prefer `--anonymize-instead` if financial/audit records must be kept.
- Use `--require-export` to ensure a safety backup is created before data is purged.
- The script generates a summary report of what was deleted in `artifacts/client-deletions/`.
- Verify that `exports/` directory is never committed, as it contains sensitive data.