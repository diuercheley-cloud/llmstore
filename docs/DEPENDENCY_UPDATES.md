# Dependency Update Policy

This document outlines the policy for automated dependency updates in the LLM Inference Stack project.

## Automated Updates

We use **Dependabot** to manage and automate dependency updates.

### Ecosystems Covered
- **Python**: Managed via `uv` (standardized as `pip` for Dependabot) in the project root.
- **Node.js**: Managed via `npm` in the root, `frontend/admin`, `frontend/client`, and `sdk/node`.
- **Docker**: Base images in Dockerfiles and `docker-compose.yml` files.
- **GitHub Actions**: Versions of actions used in `.github/workflows/`.

### Schedule
Updates are checked **weekly** (every Monday).

### Grouping Strategy
To minimize noise and CI load:
- **Minor and Patch updates** are grouped into a single Pull Request per ecosystem.
- **Major updates** are handled in separate Pull Requests to ensure careful review of breaking changes.
- **Security updates** are prioritized and handled individually as they are discovered, bypassing the weekly schedule if critical.

### Labels
- `dependencies`: General dependency update.
- `security`: Security-related update.
- Ecosystem labels: `python`, `javascript`, `docker`, `github-actions`.

## Review Process

1. **Automated Validation**: Every dependency PR must pass the full CI suite (Lint, Test, Typecheck, Security Scan).
2. **Security Priority**: PRs with the `security` label should be reviewed and merged with high priority.
3. **Manual Verification**: For Major updates, manual verification in a staging environment is recommended before merging.
