#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="$(require_api_key "${BASE_URL}" "concurrency-test")"
MODEL="${MODEL:-gemma}"

# Default parameters
START="${START:-1}"
STEP="${STEP:-2}"
MAX="${MAX:-20}"
MAX_LATENCY="${MAX_LATENCY:-30.0}"

PYTHON_BIN="python3"
if [[ -f "${ROOT_DIR}/.venv/bin/python3" ]]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"
fi

echo "Starting concurrency test for model: ${MODEL}"
echo "Base URL: ${BASE_URL}"
echo "------------------------------------------------"

"${PYTHON_BIN}" "${ROOT_DIR}/scripts/test-max-concurrency.py" \
    --url "${BASE_URL}" \
    --api-key "${API_KEY}" \
    --model "${MODEL}" \
    "$@"
