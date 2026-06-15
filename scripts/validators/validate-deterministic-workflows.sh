#!/usr/bin/env bash
set -euo pipefail

echo "Validating deterministic workflows..."

test -f control_plane/app/models/commercial_workflows.py
test -f control_plane/app/services/workflows/deterministic_orchestrator.py
test -f control_plane/app/services/workflows/workflow_receipts.py
test -f control_plane/app/services/workflows/checkpoint_replay.py
test -f control_plane/app/services/workflows/workflow_provenance.py
test -f control_plane/alembic/archive/20260515_phase55_verifiable_workflows.py
test -f docs/DETERMINISTIC_WORKFLOWS.md

grep -q "CommercialWorkflowStage" control_plane/app/models/commercial_workflows.py
grep -q "CommercialWorkflowReceipt" control_plane/app/models/commercial_workflows.py
grep -q "/admin/workflows/" control_plane/app/api/commercial_workflows_admin.py
grep -q "/portal/workflows/audit" control_plane/app/api/commercial_workflow_audit_portal.py
grep -q "Workflow DAG Viewer" control_plane/app/static/admin/index.html
grep -q "Replay Validation" control_plane/app/static/admin/index.html
grep -q "Pipeline Provenance" control_plane/app/static/admin/index.html
grep -q "Determinism Status" control_plane/app/static/admin/index.html

./venv/bin/pytest -q \
  tests/test_deterministic_workflows.py \
  tests/test_workflow_receipts.py \
  tests/test_checkpoint_replay.py \
  tests/test_workflow_provenance.py

echo "Deterministic workflows validation passed."
