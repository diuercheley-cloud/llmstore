#!/usr/bin/env bash
# Owner: platform-ops
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# Detect Python executable from virtual environment
if [[ -f "${ROOT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/.venv/bin/python3"
elif [[ -f "${ROOT_DIR}/venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/venv/bin/python3"
else
  PYTHON_EXE="python3"
fi

echo "--- Reconciling and Auditing Supported Surface Area ---"
"${PYTHON_EXE}" "${SCRIPT_DIR}/check_supported_surface.py"
