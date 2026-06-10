#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Warning: ADMIN_TOKEN env variable not set."
fi

echo "=== Agent Queue Inspection ==="

# Readiness
echo ""
echo "--- Readiness ---"
curl -fsS "${BASE_URL}/admin/agents/observability/readiness" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Unavailable"

# Jobs by status
for STATUS in queued running completed failed cancelled dead_letter; do
  echo ""
  echo "--- Jobs [${STATUS}] ---"
  RESULT=$(curl -fsS "${BASE_URL}/admin/agents/execution/jobs?status=${STATUS}" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null)
  COUNT=$(echo "${RESULT}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data if isinstance(data, list) else data.get('jobs', data.get('items', []))
    print(len(items))
except Exception:
    print('err')
" 2>/dev/null)
  echo "Count: ${COUNT}"
done

# Dead Letter Queue
echo ""
echo "--- Dead Letter Queue ---"
curl -fsS "${BASE_URL}/admin/agents/execution/dead-letter" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Unavailable"

# Active workers
echo ""
echo "--- Active Workers ---"
curl -fsS "${BASE_URL}/admin/agents/execution/workers" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null | python3 -m json.tool || echo "Unavailable"

echo ""
echo "=== Queue Inspection Complete ==="
