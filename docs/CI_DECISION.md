# CI/CD Source of Truth Decision

## Decision
As of June 2026, **GitHub Actions** is established as the primary source of truth for CI/CD pipelines in this project.

## Rationale
- **Comprehensive Coverage**: GitHub Actions currently manages the broadest range of targets, including Backend API, Frontend (Admin & Client), SDK, E2E (Playwright), Security Scans, and Documentation builds.
- **Advanced Features**: Utilizes reusable actions, complex matrix strategies, and service containers efficiently.
- **Unified Workflow**: Allows for centralized governance of the entire release process in a single platform.

## Architecture
To avoid divergence and duplication:
1. **Core Logic**: All non-trivial CI steps (build commands, test suites, integrity checks) must be implemented in the `Makefile` or in `scripts/ci/`.
2. **GitHub Actions**: Serves as the primary orchestrator, calling these scripts/Makefile targets.
3. **GitLab CI**: Maintained as a secondary/mirror pipeline for enterprise compatibility. It MUST NOT contain unique logic; it should only call the same `scripts/ci/` or `Makefile` targets used by GitHub.

## Standardization
Every CI pipeline must implement the following standardized jobs:
- `backend:lint_test`: Ruff, feature flag integrity, backend test suite.
- `frontend:lint_test_build`: Lint, build, and unit tests for both Admin and Client.
- `sdk:build_test`: Python SDK build and test suite.
- `security:scan`: Secret scanning and dependency vulnerability analysis.
- `release:gate`: Final validation steps required for a production-ready build.
