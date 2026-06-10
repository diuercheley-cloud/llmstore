#!/usr/bin/env bash
# Owner: platform-ops
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

# Detect Python executable from virtual environment
if [[ -f "${ROOT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/.venv/bin/python3"
elif [[ -f "${ROOT_DIR}/venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/venv/bin/python3"
else
  PYTHON_EXE="python3"
fi

echo "--- Running Feature Flag Policy Check ---"
bash "${SCRIPT_DIR}/check-feature-flags.sh"

echo "--- Running Feature Flag Governance Integrity Audit ---"
PYTHONPATH="${ROOT_DIR}/control_plane" "${PYTHON_EXE}" "${SCRIPT_DIR}/check-feature-flags-integrity.py"

echo "PASS: Feature flag integrity check completed successfully."
