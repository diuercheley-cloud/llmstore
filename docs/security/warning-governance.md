# Security Warning Governance Framework

This document defines the policies, schemas, and verification procedures for acknowledging and allowlisting security warnings in the repository.

## Policy Rules

1. **No Warnings in Versioned Code Files**: Real versioned source code files (`control_plane/`, `sdk/`, etc.) must never be allowlisted or bypass security scans.
2. **Permitted Scopes**: Allowlisting is strictly restricted to:
   - Gitignored artifacts (such as test backup files, temporary run files).
   - Synthetic fake test fixtures and keys clearly marked as fake.
   - Controlled test configurations.
3. **Required Metadata**: Every exception in the allowlist must have:
   - `file_path`: Exact repository-relative path to the file.
   - `justification`: Clear reasoning for why the file is safe to keep and why it triggers the warning.
   - `owner`: Person or team responsible for maintaining the exception.
   - `expiration_review_date`: A date (YYYY-MM-DD) when the exception expires and must be reviewed. Expired entries will be ignored, causing the security scan to fail.

## Schema Configuration

Exceptions are configured in `config/security-warning-allowlist.yaml`:

```yaml
allowlist:
  - file_path: "path/to/excepted-file"
    justification: "Detailed explanation of safety and synthetic nature"
    owner: "owner-name"
    expiration_review_date: "YYYY-MM-DD"
```

## Validation & Expiration

The security scanner validation automatically checks that:
- The path is NOT tracked or staged in Git.
- All three metadata fields (`justification`, `owner`, `expiration_review_date`) are present.
- The `expiration_review_date` is in the future.
