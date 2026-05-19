# Security Report
**Date:** 2026-05-19T19:59:18.161926
**Score:** PASS_WITH_WARNINGS
**Branch:** release/v1.8.3 (555fd17cdbd1461ee7b8a74d2b77289672ecfe58)

## Summary
- **Blocking Findings:** 0
- **Warnings:** 8
- **Informational/Redacted:** 3
- **Passed Checks:** 21

## Blocking Findings (Action Required)
_No findings in this category._


## Warnings
| ID | Category | Title | Status | Severity | Details |
|---|---|---|---|---|---|
| sec-secrets-artifacts-recent-generated_artifact-0 | Secrets | generated_artifact (recent artifacts) | warn | medium | Found secrets in generated artifacts for recent artifacts. (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-recent-generated_artifact-1 | Secrets | generated_artifact (recent artifacts) | warn | medium | Found secrets in generated artifacts for recent artifacts. (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-recent-generated_artifact-2 | Secrets | generated_artifact (recent artifacts) | warn | medium | Found secrets in generated artifacts for recent artifacts. (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-recent-generated_artifact-3 | Secrets | generated_artifact (recent artifacts) | warn | medium | Found secrets in generated artifacts for recent artifacts. (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-generated_artifact-0 | Secrets | generated_artifact (artifacts/releases (legacy)) | warn | medium | Found secrets in generated artifacts for artifacts/releases (legacy). (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-generated_artifact-1 | Secrets | generated_artifact (artifacts/releases (legacy)) | warn | medium | Found secrets in generated artifacts for artifacts/releases (legacy). (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-generated_artifact-2 | Secrets | generated_artifact (artifacts/releases (legacy)) | warn | medium | Found secrets in generated artifacts for artifacts/releases (legacy). (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |
| sec-secrets-artifacts-generated_artifact-3 | Secrets | generated_artifact (artifacts/releases (legacy)) | warn | medium | Found secrets in generated artifacts for artifacts/releases (legacy). (File: artifacts/local-production-validation/20260519T161224/logs/pytest.log) |


## Informational & Redacted Artifacts
| ID | Category | Title | Status | Severity | Details |
|---|---|---|---|---|---|
| sec-secrets-artifacts-recent | Secrets | Secrets scan (recent artifacts) | warn | high | Classified 4 finding(s) for recent artifacts. |
| sec-secrets-artifacts | Secrets | Secrets scan (artifacts/releases (legacy)) | warn | high | Classified 4 finding(s) for artifacts/releases (legacy). |
| perm-pem-keys | Permissions | Check for .pem/.key files | skip | low | Only authorized fake fixtures found (3). |


## All Passed Checks
| ID | Category | Title | Status | Severity | Details |
|---|---|---|---|---|---|
| sec-secrets-versionable | Secrets | Secrets scan (versionable files) | pass | low | No secret findings. |
| sec-secrets-all | Secrets | Secrets scan (all files (legacy)) | pass | low | No secret findings. |
| sec-secrets-staged | Secrets | Secrets scan (staged files) | pass | low | No secret findings. |
| sec-secrets-releases-versioned | Secrets | Secrets scan (versioned releases) | pass | low | No secret findings. |
| sec-secrets-releases-untracked | Secrets | Secrets scan (untracked releases) | pass | low | No secret findings. |
| sec-secrets-artifacts-ignored | Secrets | Secrets scan (ignored artifacts) | pass | low | No secret findings. |
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
