#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Activate virtual environment if available
if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.venv/bin/activate"
fi

# Execute the python runner
exec python "${ROOT_DIR}/scripts/benchmark_model_local_runner.py" "$@"
