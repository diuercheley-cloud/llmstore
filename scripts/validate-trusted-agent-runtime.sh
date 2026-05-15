#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "[trusted-agent-runtime] validating local assets"
python3 -m py_compile \
  control_plane/app/models/commercial_agents.py \
  control_plane/app/services/agents/trusted_agent_runtime.py \
  control_plane/app/services/agents/tool_policy_engine.py \
  control_plane/app/services/agents/action_replay.py \
  control_plane/app/services/agents/execution_receipts.py \
  control_plane/app/api/commercial_trusted_agents_admin.py \
  control_plane/app/api/commercial_agent_audit_portal.py

echo "[trusted-agent-runtime] validating tests, docs and migration"
test -f tests/test_trusted_agent_runtime.py
test -f tests/test_tool_policy_engine.py
test -f tests/test_agent_replay.py
test -f tests/test_agent_receipts.py
test -f docs/TRUSTED_AGENT_RUNTIME.md
test -f control_plane/alembic/versions/20260515_phase54_agentic_execution.py

echo "[trusted-agent-runtime] running focused pytest"
PYTEST_BIN="pytest"
if [[ -x "./venv/bin/pytest" ]]; then
  PYTEST_BIN="./venv/bin/pytest"
fi

"${PYTEST_BIN}" -q \
  tests/test_trusted_agent_runtime.py \
  tests/test_tool_policy_engine.py \
  tests/test_agent_replay.py \
  tests/test_agent_receipts.py

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "[trusted-agent-runtime] ADMIN_TOKEN not set; skipping live endpoint validation"
  exit 0
fi

auth_header=("X-Admin-Token: ${ADMIN_TOKEN}")

echo "[trusted-agent-runtime] runtime status"
curl -fsS "${BASE_URL}/admin/agents/runtime/status" -H "${auth_header[0]}" >/dev/null

echo "[trusted-agent-runtime] tools list"
curl -fsS "${BASE_URL}/admin/agents/tools" -H "${auth_header[0]}" >/dev/null

echo "[trusted-agent-runtime] replay records"
curl -fsS "${BASE_URL}/admin/agents/replay/records" -H "${auth_header[0]}" >/dev/null

echo "[trusted-agent-runtime] validation completed"
