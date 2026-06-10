#!/usr/bin/env bash
set -euo pipefail

echo "Validating workflow governance enforcement..."

test -f control_plane/app/models/commercial_workflows.py
test -f control_plane/app/services/workflows/workflow_policy_enforcement.py
test -f control_plane/app/services/workflows/workflow_approval_chain.py
test -f control_plane/app/services/workflows/workflow_replay_sessions.py
test -f control_plane/app/services/workflows/workflow_governance_ledger.py
test -f control_plane/app/api/commercial_workflow_governance_portal.py
test -f control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py
test -f docs/WORKFLOW_GOVERNANCE_ENFORCEMENT.md

grep -q "CommercialWorkflowPolicyBinding" control_plane/app/models/commercial_workflows.py
grep -q "CommercialWorkflowApproval" control_plane/app/models/commercial_workflows.py
grep -q "CommercialWorkflowGovernanceEvent" control_plane/app/models/commercial_workflows.py
grep -q "/admin/workflows/governance/" control_plane/app/api/commercial_workflows_admin.py
grep -q "/portal/workflows/governance/" control_plane/app/api/commercial_workflow_governance_portal.py

./venv/bin/pytest -q \
  tests/test_workflow_policy_enforcement.py \
  tests/test_workflow_approval_chain.py \
  tests/test_workflow_governance_ledger.py \
  tests/test_workflow_replay_sessions.py

echo "Workflow governance validation passed."
