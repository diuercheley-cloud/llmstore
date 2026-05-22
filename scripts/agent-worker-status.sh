#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Warning: ADMIN_TOKEN env variable not set."
fi

echo "=== Agent Worker Status ==="

# Get worker heartbeats from the readiness endpoint
echo ""
echo "--- Readiness Check ---"
curl -fsS "${BASE_URL}/admin/agents/observability/readiness" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Readiness endpoint unavailable"

echo ""
echo "--- Active Workers ---"
curl -fsS "${BASE_URL}/admin/agents/execution/workers" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Workers endpoint unavailable"

echo ""
echo "--- Queue Summary ---"
curl -fsS "${BASE_URL}/admin/agents/execution/jobs" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Jobs endpoint unavailable"
