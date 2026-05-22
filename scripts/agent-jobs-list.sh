#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

# Optional tenant ID header
TENANT_HEADER=()
if [[ -n "${TENANT_ID:-}" ]]; then
  TENANT_HEADER=(-H "X-Tenant-ID: ${TENANT_ID}")
fi

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Warning: ADMIN_TOKEN env variable not set."
fi

curl -fsS "${BASE_URL}/admin/agents/execution/jobs" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "${TENANT_HEADER[@]}" \
  | python3 -m json.tool
