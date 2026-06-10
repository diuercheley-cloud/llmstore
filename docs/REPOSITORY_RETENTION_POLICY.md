# Repository Retention Policy

## Objective
Minimize repository footprint and noise by enforcing strict retention for build artifacts, evidence, and ephemeral data.

## Retention Rules
1. **Source Code & Configs**: Permanent.
2. **Build Artifacts (`dist/`, `build/`)**: Ephemeral. Never committed.
3. **Test Data & Backups (`artifacts/`, `backups/`)**:
    - **Local**: Ephemeral. Cleaned up automatically on local runs.
    - **CI/CD**: Uploaded to GitHub Actions artifacts, retained for 7 days.
    - **Production**: Stored in designated external storage.
4. **Documentation**: Keep current version. Archive legacy versions in a separate `docs/archive` folder if required.
5. **Secrets & Keys**: **Never commit**. Use `.gitignore` to prevent leakage.

## Enforcement
- CI pipelines MUST fail if prohibited patterns (e.g., `.pem` keys, large logs) are detected in the commit history or staged area.
- Periodic hygiene checks must be performed using `scripts/repo_hygiene_check.sh`.
