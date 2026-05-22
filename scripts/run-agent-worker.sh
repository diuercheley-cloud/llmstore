#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
init_stack_env

PYTHON_EXEC="${ROOT_DIR}/.venv/bin/python"
if [[ ! -f "${PYTHON_EXEC}" ]]; then
  PYTHON_EXEC="python3"
fi

echo "Starting Agent Worker..."
export PYTHONPATH="${ROOT_DIR}/control_plane:${PYTHONPATH:-}"

export AGENT_EXECUTION_PLANE_ENABLED="${AGENT_EXECUTION_PLANE_ENABLED:-true}"
export AGENT_WORKER_ENABLED="${AGENT_WORKER_ENABLED:-true}"
export AGENT_RUNTIME_ENABLED="${AGENT_RUNTIME_ENABLED:-true}"

exec "${PYTHON_EXEC}" -m app.workers.agent_worker "$@"
