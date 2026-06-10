#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN}"
MONTH="${1:-${MONTH:-}}"

if [[ -n "${MONTH}" ]]; then
  curl -fsS "${BASE_URL}/admin/reports/monthly?month=${MONTH}" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
  exit 0
fi

curl -fsS "${BASE_URL}/admin/reports/monthly" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool
