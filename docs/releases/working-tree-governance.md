---
owner: platform-ops
status: consolidated
---

# Working Tree Governance

This document defines the policies and procedures for maintaining a clean and audit-ready working tree for the LLM Inference Stack releases.

## Core Principles

1.  **Reproducibility**: The working tree must reflect exactly what is versioned in the repository. Local changes or untracked artifacts must not interfere with the build or release process.
2.  **Auditability**: Every file in the release bundle must have a clear lineage and purpose.
3.  **Zero Drift**: Real configuration (`.env`), private keys, and runtime artifacts must never be committed.

## Governance Rules

- **Ignore Patterns**: The `.gitignore` file is the source of truth for excluded artifacts. It must include:
    - Real `.env` files.
    - Private keys and certificates (except test fixtures).
    - Runtime logs and caches (`.pytest_cache`, `.ruff_cache`, etc.).
    - Database files (`*.db`, `*.sqlite`).
    - Large model binaries (`*.gguf`, `*.bin`).
    - Temporary release bundles and tarballs.

- **Mandatory Checks**:
    - Before any release, `make stabilization-check` must be executed.
    - This target invokes `scripts/validators/check-working-tree-clean.sh`, which fails if there are uncommitted changes or untracked files that are not ignored.

- **Artifact Management**:
    - Legitimate non-code artifacts (e.g., screenshots for documentation) should be stored in `artifacts/` and managed according to the project's documentation policy.

## Validation Script: `check-working-tree-clean.sh`

This script performs the following checks:
1.  **Git Status Cleanliness**: Ensures no uncommitted changes exist.
2.  **Sensitive File Leak Detection**: Explicitly searches for common sensitive filenames like `.env` or `ca.key`.
3.  **Secret Scanning**: Basic pattern matching for API keys in tracked files.
4.  **Alembic Integrity**: Indirectly checked via git status (untracked migrations).
5.  **Untracked File Detection**: Ensures no files exist that are neither tracked nor ignored.

## Enforcement

Integration with the CI/CD pipeline and local Makefile targets ensures that a release cannot be finalized if the working tree is in a "dirty" or "drifting" state.
