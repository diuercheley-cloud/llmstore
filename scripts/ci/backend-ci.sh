#!/bin/bash
set -e

# LLM Inference Stack - Backend CI
# Source of truth: docs/CI_DECISION.md

echo "==> Backend CI: Linting and Integrity"
ruff check .
ruff format --check .
make platform-freeze-check
make check-feature-flags-integrity
make check-supported-surface
PYTHONPATH=.:control_plane python3 scripts/validators/check-maintenance-budgets.py
bash scripts/validators/check-secrets.sh --all

echo "==> Backend CI: Surface Governance"
make generate-route-surface
make validate-route-surface
make validate-deprecated-surface

echo "==> Backend CI: Contract Tests"
pytest tests/contract/test_openapi_snapshot.py -q

echo "==> Backend CI: Database Migrations"
cd control_plane
alembic upgrade heads
cd ..

echo "==> Backend CI: Tests"
export PYTHONPATH=.:control_plane
pytest tests/control_plane -m "release_gate" --cov --cov-report=xml:control_plane/coverage.xml --junitxml=artifacts/reports/api-release-gate.xml
pytest tests/integration/contracts tests/integration/quality tests/integration/security -m "release_gate"

echo "==> Backend CI: Coverage Gates"
python3 scripts/validators/check-core-coverage-gates.py

echo "==> Backend CI: Backup Components"
export BACKUP_RESTORE_ENABLED="true"
make test-backup-components
