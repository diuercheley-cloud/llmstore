#!/bin/bash
# scripts/validators/check-script-manifest.sh
# Entrypoint for operational scripts governance validation.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_EXEC="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXEC=".venv/bin/python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_EXEC="venv/bin/python3"
fi

echo "--- Starting Operational Scripts Governance Compliance Audit ---"
PYTHONPATH="${ROOT_DIR}/control_plane" ${PYTHON_EXEC} scripts/legacy/check_script_manifest.py
