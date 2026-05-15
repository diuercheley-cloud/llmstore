#!/usr/bin/env bash
set -euo pipefail

echo "Validating Phase 56 migrations..."

test -f control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py
grep -q 'down_revision = "20260515_phase55"' control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py
grep -q "_json_type" control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py
grep -q "_uuid_type" control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py
grep -q "tenant_id" control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py

./venv/bin/pytest -q \
  tests/test_phase56_migration_sqlite.py \
  tests/test_phase56_migration_postgres.py

echo "Phase 56 migration validation passed."
