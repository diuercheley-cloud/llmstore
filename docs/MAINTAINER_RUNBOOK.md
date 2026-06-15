# Maintainer Runbook

This document is the source of truth for maintainers of the LLM Inference Stack. It covers critical operational procedures.

## 1. Local Environment Setup

To start a full development environment:

```bash
# 1. System dependencies and venv
make install

# 2. Environment variables
cp .env.example .env.local
# Edit .env.local with your credentials

# 3. Infrastructure
docker compose up -d postgres redis

# 4. Database Migrations
source .venv/bin/activate
alembic upgrade head

# 5. Start Backend
make run

# 6. Start Frontend (separate terminal)
cd frontend/admin
npm install && npm run dev
```

## 2. Running Tests

Maintainers must ensure all tests pass before any release.

```bash
# Full validation suite
make validate-all

# Backend tests
make backend-test

# Frontend tests
cd frontend/admin && npm run test
```

## 3. Release Process

Releases are automated via scripts. Always release from a clean main branch.

```bash
# 1. Run release gate validation
make release-gate TAG=vX.Y.Z

# 2. Execute local production release
bash scripts/release/release-local-production.sh --version vX.Y.Z-local-production

# 3. Create release bundle
make release TAG=vX.Y.Z
```

## 4. Rollback Process

If a release fails or introduces critical bugs:

```bash
# 1. Execute rollback script
bash scripts/release/rollback-release.sh

# 2. For a simulated dry-run first:
bash scripts/release/rollback-release.sh --dry-run
```

## 5. Backup and Restore

### Create Backup
```bash
bash scripts/backup/backup.sh
```

### Restore Backup
```bash
bash scripts/backup/restore.sh /path/to/backup/postgres.dump
```

## 6. Incident Response

1. **Verify Health**: Check `http://localhost:8080/ready` and logs in `logs/`.
2. **Isolate**: If a specific service is failing (e.g., Worker), restart only that service.
3. **Rollback**: If the issue started after a release, perform a rollback immediately.
4. **Logs Analysis**: Use `docker compose logs -f` for infra and check `artifacts/reports` for recent validation failures.
