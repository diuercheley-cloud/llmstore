#!/bin/bash
# scripts/check-api-surface.sh
# Entrypoint for API Surface classification validation.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_EXEC="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXEC=".venv/bin/python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_EXEC="venv/bin/python3"
fi

echo "--- Starting API Surface Area Compliance Audit ---"
PYTHONPATH="${ROOT_DIR}/control_plane" ${PYTHON_EXEC} scripts/check_api_surface.py
