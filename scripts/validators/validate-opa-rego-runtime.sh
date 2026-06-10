#!/bin/bash
set -e

echo "Validating OPA/Rego Policy Runtime Integration (Phase 61)..."

echo "1. Checking Python Syntax..."
python3 -m py_compile control_plane/app/models/commercial_policy_runtime.py
python3 -m py_compile control_plane/alembic/versions/20260515_phase61_opa_rego_policy_runtime.py
python3 -m py_compile control_plane/app/services/governance/rego_runtime.py
python3 -m py_compile control_plane/app/services/governance/policy_evaluator.py
python3 -m py_compile control_plane/app/services/governance/policy_trace.py
python3 -m py_compile control_plane/app/api/commercial_policy_runtime_admin.py

echo "2. Running Pytest for Policy Runtime..."
# Assuming pytest is available in the environment
cd control_plane
pytest tests/test_rego_runtime.py tests/test_policy_evaluator.py tests/test_policy_trace.py tests/test_policy_runtime_integration.py -v

echo "3. Checking bash scripts syntax..."
bash -n ../scripts/validators/validate-opa-rego-runtime.sh

echo "Validation Complete. Phase 61 OPA/Rego Integration looks good."
