# Release Artifacts Security Policy

This document defines the security standards for files located in the `releases/` directory. These files are versioned and must not contain any sensitive information.

## Allowed Files

The following files **can** be versioned in `releases/<version>/`:

- `summary.json`: High-level summary of validation results (redacted).
- `summary.md`: Human-readable summary of validation results (redacted).
- `release-manifest.json`: Metadata about the release.
- `bundle-manifest.json`: Metadata about the release bundle content.
- `bundle-checksums.sha256`: SHA256 hashes of the release tarballs (which are NOT versioned).
- `LOCAL_PRODUCTION_VALIDATION.md`: Documentation related to the release.
- `LOCAL_PRODUCTION_RUNBOOK.md`: Instructions for the release.

## Prohibited Files

The following files **must NEVER** be versioned in the repository:

- `*.tar.gz`, `*.zip`, `*.7z`: Release bundles containing the codebase. These are too large and may contain artifacts not yet scanned.
- `logs/` directories: Raw logs often contain sensitive data, tokens, or PII.
- `.env`, `.env.local`: Environment files containing real credentials.
- `*.pem`, `*.key`, `*.crt`: Private keys or certificates.
- `*.db`, `*.sqlite`: Database files.

## Sensitive Content Restrictions

No versioned file in `releases/` may contain:

- **API Keys:** OpenAI (sk-...), AWS, etc.
- **Tokens:** ADMIN_TOKEN, Bearer tokens, JWTs, GitHub PATs (ghp_...).
- **Headers:** Authorization headers with real values.
- **Environment Variables:** Real values from `.env` files.
- **Sensitive Prompts:** Full system prompts that are considered intellectual property or sensitive.
- **RAG Content:** Actual document content from RAG uploads.

## How to Generate a Secure Release

1.  Use `scripts/release-local-production.sh`.
2.  The script automatically calls `scripts/redact-local-sensitive-artifacts.sh` to clean up artifacts before moving them to the `releases/` directory.
3.  The script also runs `scripts/validate-release-artifacts-security.sh` to ensure no secrets leaked.

## How to Validate

Run the validation script manually at any time:

```bash
./scripts/validate-release-artifacts-security.sh
```

To validate a specific release directory:

```bash
./scripts/validate-release-artifacts-security.sh --release-dir releases/v1.5.5-example
```

## Remediation

If a secret is inadvertently committed to `releases/`:

1.  **Rotate the secret immediately.** This is the most important step.
2.  Remove the file or fix the content.
3.  Use `git filter-repo` or `BFG Repo-Cleaner` to remove the sensitive data from git history if necessary (follow company security protocols).
4.  Update the redaction rules in `scripts/redact-local-sensitive-artifacts.sh` if the secret was missed by the automatic process.
