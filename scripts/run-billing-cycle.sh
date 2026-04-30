#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

if response="$(curl -fsS "${BASE_URL}/admin/billing/run-cycle" -H "X-Admin-Token: ${ADMIN_TOKEN}" -X POST 2>/dev/null)"; then
  printf '%s\n' "${response}" | python3 -m json.tool
  exit 0
fi

dc exec -T control-plane bash -lc \
  "curl -fsS http://localhost:8080/admin/billing/run-cycle -H 'X-Admin-Token: ${ADMIN_TOKEN}' -X POST" | python3 -m json.tool
