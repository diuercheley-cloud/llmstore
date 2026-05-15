#!/usr/bin/env bash
set -e

echo "Starting Validation for Governance Supervisor AI..."

# 1. Run formatting/linting checks
echo "Running code validation..."
python3 -m py_compile control_plane/app/services/governance/governance_supervisor.py
python3 -m py_compile control_plane/app/services/governance/governance_risk_engine.py
python3 -m py_compile control_plane/app/services/governance/governance_autoremediation.py
python3 -m py_compile control_plane/app/services/governance/governance_decision_explainer.py
python3 -m py_compile control_plane/app/models/commercial_governance_supervisor.py
python3 -m py_compile control_plane/app/api/commercial_governance_supervisor_admin.py

# 2. Run specific tests
echo "Running pytest for Governance Supervisor components..."
pytest tests/test_governance_supervisor.py
pytest tests/test_governance_risk_engine.py
pytest tests/test_governance_autoremediation.py
pytest tests/test_governance_explainability.py

echo "Validation Complete. The Governance Supervisor AI components are structurally sound."
