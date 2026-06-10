# Security Report
**Date:** 2026-05-23T08:06:22.042237
**Score:** PASS
**Branch:** release/v2.0.0 (1460aca530b3f2e7c09fd76c3e35360a82b62c7e)

## Summary
- **Blocking Findings:** 0
- **Warnings:** 0
- **Informational/Redacted:** 5
- **Passed Checks:** 23

## Blocking Findings (Action Required)
_No findings in this category._


## Warnings
_No findings in this category._


## Informational & Redacted Artifacts
| ID | Category | Title | Status | Severity | Details |
|---|---|---|---|---|---|
| sec-secrets-artifacts-ignored-generated_artifact-0 | Secrets | generated_artifact (ignored artifacts) | skip | low | [Allowlisted] Found secrets in generated artifacts for ignored artifacts. (Allowlisted by security-team until 2027-05-23 (Reason: Synthetic gitignored backup artifact containing fake credentials for backup restore testing)) (File: artifacts/backups/test-backup-run/config/config.env) |
| sec-secrets-artifacts-ignored-generated_artifact-1 | Secrets | generated_artifact (ignored artifacts) | skip | low | [Allowlisted] Found secrets in generated artifacts for ignored artifacts. (Allowlisted by security-team until 2027-05-23 (Reason: Synthetic gitignored backup artifact containing fake credentials for backup restore testing)) (File: artifacts/backups/test-backup-run/config/config.env) |
| sec-secrets-artifacts-generated_artifact-0 | Secrets | generated_artifact (artifacts/releases (legacy)) | skip | low | [Allowlisted] Found secrets in generated artifacts for artifacts/releases (legacy). (Allowlisted by security-team until 2027-05-23 (Reason: Synthetic gitignored backup artifact containing fake credentials for backup restore testing)) (File: artifacts/backups/test-backup-run/config/config.env) |
| sec-secrets-artifacts-generated_artifact-1 | Secrets | generated_artifact (artifacts/releases (legacy)) | skip | low | [Allowlisted] Found secrets in generated artifacts for artifacts/releases (legacy). (Allowlisted by security-team until 2027-05-23 (Reason: Synthetic gitignored backup artifact containing fake credentials for backup restore testing)) (File: artifacts/backups/test-backup-run/config/config.env) |
| perm-pem-keys | Permissions | Check for .pem/.key files | skip | low | Only authorized fake fixtures found (3). |


## All Passed Checks
| ID | Category | Title | Status | Severity | Details |
|---|---|---|---|---|---|
| sec-secrets-versionable | Secrets | Secrets scan (versionable files) | pass | low | No secret findings. |
| sec-secrets-all | Secrets | Secrets scan (all files (legacy)) | pass | low | No secret findings. |
| sec-secrets-staged | Secrets | Secrets scan (staged files) | pass | low | No secret findings. |
| sec-secrets-releases-versioned | Secrets | Secrets scan (versioned releases) | pass | low | No secret findings. |
| sec-secrets-releases-untracked | Secrets | Secrets scan (untracked releases) | pass | low | No secret findings. |
| sec-secrets-artifacts-ignored | Secrets | Secrets scan (ignored artifacts) | pass | low | Classified 2 finding(s) for ignored artifacts. |
| sec-secrets-artifacts-recent | Secrets | Secrets scan (recent artifacts) | pass | low | No secret findings. |
| sec-secrets-artifacts | Secrets | Secrets scan (artifacts/releases (legacy)) | pass | low | Classified 2 finding(s) for artifacts/releases (legacy). |
| git-env | Git hygiene | Check .env is not versioned | pass | critical | .env not tracked. |
| git-env-local | Git hygiene | Check .env.local is not versioned | pass | critical | .env.local not tracked. |
| git-local-dir | Git hygiene | Check .local/ is not versioned | pass | high | .local/ not tracked. |
| git-models | Git hygiene | Check models/ is not versioned | pass | high | models/ not tracked. |
| git-gguf | Git hygiene | Check *.gguf is not versioned | pass | high | *.gguf not tracked. |
| git-rag-uploads | Git hygiene | Check data/rag_uploads/ is not versioned | pass | high | data/rag_uploads/ not tracked. |
| git-backups | Git hygiene | Check backups/ is not versioned | pass | high | backups/ not tracked. |
| git-exports | Git hygiene | Check exports/ is not versioned | pass | high | exports/ not tracked. |
| perm-scripts | Permissions | Check shell scripts permissions | pass | medium | All scripts executable. |
| perm-env-local | Permissions | Check .env.local permissions | pass | medium | Permissions restricted. |
| api-admin-token | Admin/API | Admin endpoints require token | pass | high | Got 401 as expected from /admin/clients. |
| log-env | Logs/artifacts | Logs do not contain secrets | pass | high | No env variables found in logs. |
| rag-git | RAG/TTS data | RAG uploads outside git | pass | medium | Checked by git hygiene. |
| docker-expose | Docker | Docker-compose does not expose DB ports globally | pass | high | DB ports not globally exposed. |
| docker-privileged | Docker | Containers do not use privileged mode | pass | high | No privileged containers. |
