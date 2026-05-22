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

echo "=== Agent Worker Drain ==="
echo "This will cancel all queued jobs and mark the current worker as inactive."

# Get list of queued jobs
echo ""
echo "Fetching queued jobs..."
QUEUED_JOBS=$(curl -fsS "${BASE_URL}/admin/agents/execution/jobs?status=queued" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "[]")

JOB_COUNT=$(echo "$QUEUED_JOBS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data if isinstance(data, list) else data.get('jobs', data.get('items', []))))" 2>/dev/null || echo "0")

echo "Queued jobs found: ${JOB_COUNT}"

if [[ "${JOB_COUNT}" -gt 0 ]]; then
  echo ""
  read -p "Cancel all ${JOB_COUNT} queued jobs? [y/N] " CONFIRM
  if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo "Drain cancelled."
    exit 0
  fi

  # Cancel each queued job
  JOB_IDS=$(echo "$QUEUED_JOBS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data if isinstance(data, list) else data.get('jobs', data.get('items', []))
for j in items:
    print(j.get('id', j.get('job_id', '')))
" 2>/dev/null)

  for JOB_ID in ${JOB_IDS}; do
    if [[ -n "${JOB_ID}" ]]; then
      echo "Cancelling job ${JOB_ID}..."
      curl -fsS -X POST "${BASE_URL}/admin/agents/execution/jobs/${JOB_ID}/cancel" \
        -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "  Failed to cancel ${JOB_ID}"
    fi
  done

  echo "Drain complete: ${JOB_COUNT} jobs cancelled."
else
  echo "No queued jobs to drain."
fi
