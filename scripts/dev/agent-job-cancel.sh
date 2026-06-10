#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
JOB_ID="${1:-}"

if [[ -z "${JOB_ID}" ]]; then
  echo "Usage: $0 <job-id>"
  exit 1
fi

TENANT_HEADER=()
if [[ -n "${TENANT_ID:-}" ]]; then
  TENANT_HEADER=(-H "X-Tenant-ID: ${TENANT_ID}")
fi

curl -fsS -X POST "${BASE_URL}/admin/agents/execution/jobs/${JOB_ID}/cancel" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "${TENANT_HEADER[@]}" \
  | python3 -m json.tool
