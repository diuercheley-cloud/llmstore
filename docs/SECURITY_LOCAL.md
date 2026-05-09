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

## Key and Certificate Policy
To prevent accidental leakage of real private keys or certificates:
- **Never commit real keys**: All `.pem` and `.key` files are blocked by `.gitignore` by default.
- **Authorized Fixtures**: Only fake fixtures used for testing are allowed. They MUST:
    - Reside in `tests/fixtures/`
    - Be named `fake_*.pem` or `fake_*.key`
    - Contain the marker text: `FAKE TEST KEY - DO NOT USE`
- **Validation**: Use `./scripts/validate-key-files-local.sh` to verify compliance.

## Common Warnings and Fixes
- **Unrestricted `.env.local` permissions**: Fix with `make fix-permissions` or `chmod 600 .env.local`.
- **Non-executable scripts**: Fix with `make fix-permissions` or `chmod +x scripts/*.sh`.
- **Exposed Database Ports**: Ensure your `docker-compose.yml` binds ports strictly to localhost (e.g., `127.0.0.1:5432:5432`).

## Permission Management
The project includes automated tools to manage and validate file permissions:
- `make fix-permissions`: Applies the standard security permissions (e.g., +x for scripts, 600 for .env.local).
- `make validate-permissions`: Checks if the project adheres to these standards.

## What NEVER to Commit
Do not commit the following to the repository:
- `.env`, `.env.local`
- Files within `.local/`
- Downloaded models (`models/`, `*.gguf`, `*.safetensors`)
- User uploaded RAG data (`data/rag_uploads/`)
- Backups and Exports (`backups/`, `exports/`, `artifacts/`)
- Release archives (`releases/**/*.tar.gz`)

**Validation:**
We strictly enforce this policy via `.gitignore`. You can validate the rules by running:
```bash
./scripts/validate-gitignore-security.sh
```

## Secrets Policy
- Run `make check-secrets` locally to detect leaked tokens.
- We never check in production or high-privileged API keys.
- Hash or mask API keys in logs.
- `scripts/check-secrets.sh` supports:
  - `--all` to scan versioned files
  - `--staged` to scan only staged changes
  - `--path <path>` to scan a specific tree, including temporary test output
  - `--verbose` to print the classification for each finding

## Safe Fixture Policy
Some tests intentionally validate secret scanners. Those fixtures are allowed only when all conditions below are true:
- The path starts with `tests/fixtures/`
- The filename contains `fake_` or `fixture_`
- The file content contains `FAKE SECRET FOR TESTS ONLY` or `FAKE TEST KEY - DO NOT USE`
- The file is not under `releases/`, `docs/`, `scripts/`, or `control_plane/`

Everything else is treated as suspicious. This includes:
- Real or fake `ADMIN_TOKEN` values outside approved fixtures
- Real bearer tokens outside approved fixtures
- Real `.env` or `.env.local` files
- Secrets inside `releases/` or generated `artifacts/`

Classifications emitted by the local scanners:
- `real_secret_suspected`: blocking failure
- `fixture_expected`: allowed fake fixture, reported as informational skip
- `generated_artifact`: warning for generated files that contain secrets
- `obsolete_release_file`: warning for release bundles or release-side leftovers
- `needs_review`: suspicious item that still needs manual confirmation

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

## Security Cleanup Workflow
For major releases or hardening sprints (like v1.5.4), follow this diagnostic workflow:

1. **Diagnostic Phase**:
   - Run baseline reports: `./scripts/check-secrets.sh --all` and `./scripts/security-report-local.sh`.
   - Create a safe diagnostic document: `docs/SECURITY_CLEANUP_<version>.md`.
   - Use `scripts/parse-security-report-local.sh` to get a masked summary of issues.
   - Categorize each issue: `real_risk`, `fixture_expected`, `generated_artifact`, `permission_issue`, etc.

2. **Remediation Phase**:
   - Fix `permission_issue` and `real_risk` items first.
   - Purge `generated_artifact` from local storage.
   - For `fixture_expected` or false positives, update the security scripts to exclude these specific patterns.
   - Never commit raw secrets during the cleanup process.

3. **Validation Phase**:
   - Re-run the security report.
   - Score should move from `FAIL` or `PASS_WITH_WARNINGS` towards `PASS`.
   - Update the diagnostic document with the new status for each item.
