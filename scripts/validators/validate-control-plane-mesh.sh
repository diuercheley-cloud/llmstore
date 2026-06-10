#!/bin/bash
set -e

echo "========================================================"
echo "Phase 63: Distributed Sovereign Control Plane Mesh Validation"
echo "========================================================"

cd control_plane

echo "[1/4] Running Alembic configuration checks..."
# Verify migration file syntax
python3 -m py_compile alembic/versions/phase63_control_plane_mesh.py

echo "[2/4] Running unit tests for Mesh services..."
# Activate venv if it exists and run pytest
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

PYTHONPATH=. pytest tests/test_control_plane_mesh.py
PYTHONPATH=. pytest tests/test_mesh_consensus.py
PYTHONPATH=. pytest tests/test_mesh_replication.py
PYTHONPATH=. pytest tests/test_mesh_failover.py

echo "[3/4] Syntax check for Mesh API and Main..."
python3 -m py_compile app/api/commercial_mesh_admin.py
python3 -m py_compile app/main.py

echo "[4/4] Validating script syntax..."
cd ..
bash -n scripts/validators/validate-control-plane-mesh.sh

echo "========================================================"
echo "✅ Validation successful: Control Plane Mesh (Phase 63)"
echo "========================================================"
