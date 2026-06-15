#!/usr/bin/env bash
set -euo pipefail

PYTEST_BIN="${PYTEST_BIN:-}"
if [[ -z "${PYTEST_BIN}" ]]; then
  if [[ -x "./.venv/bin/pytest" ]]; then
    PYTEST_BIN="./.venv/bin/pytest"
  elif [[ -x "./venv/bin/pytest" ]]; then
    PYTEST_BIN="./venv/bin/pytest"
  else
    PYTEST_BIN="pytest"
  fi
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Validating federated deterministic workflows..."

test -f control_plane/app.models.commercial.commercial_federated_workflows.py
test -f control_plane/app/services/workflows/federated_execution.py
test -f control_plane/app/services/workflows/federated_consensus.py
test -f control_plane/app/services/workflows/federated_replay.py
test -f control_plane/app/services/workflows/workflow_execution_leases.py
test -f control_plane/app/api/commercial_federated_workflows_admin.py
test -f control_plane/alembic/archive/20260515_phase57_federated_deterministic_workflows.py
test -f docs/FEDERATED_DETERMINISTIC_WORKFLOWS.md

grep -q "CommercialFederatedWorkflowExecution" control_plane/app.models.commercial.commercial_federated_workflows.py
grep -q "/admin/workflows/federation/overview" control_plane/app/api/commercial_federated_workflows_admin.py
grep -q "Federated Deterministic Multi-Cluster Workflow Execution" control_plane/app/static/admin/index.html
grep -q "Workflow Federation Status" control_plane/app/static/portal/index.html

"${PYTEST_BIN}" -q \
  tests/test_federated_workflows.py \
  tests/test_federated_replay.py \
  tests/test_workflow_consensus.py \
  tests/test_workflow_execution_leases.py \
  tests/test_deterministic_workflows.py

"${PYTHON_BIN}" -m py_compile \
  control_plane/app.models.commercial.commercial_federated_workflows.py \
  control_plane/app/services/workflows/federated_execution.py \
  control_plane/app/services/workflows/federated_consensus.py \
  control_plane/app/services/workflows/federated_replay.py \
  control_plane/app/services/workflows/workflow_execution_leases.py \
  control_plane/app/api/commercial_federated_workflows_admin.py

bash -n scripts/validators/validate-federated-workflows.sh

echo "Federated deterministic workflows validation passed."
