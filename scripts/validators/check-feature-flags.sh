#!/usr/bin/env bash
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
export PYTHONPATH="${ROOT_DIR}/control_plane:${ROOT_DIR}/scripts:${PYTHONPATH:-}"

# Run python validator
"${PYTHON_EXE}" "${SCRIPT_DIR}/check-feature-flags.py"
