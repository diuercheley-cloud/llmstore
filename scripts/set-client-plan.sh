#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

CLIENT_ID="${1:?usage: ./scripts/set-client-plan.sh CLIENT_ID PLAN_CODE}"
PLAN_CODE="${2:?usage: ./scripts/set-client-plan.sh CLIENT_ID PLAN_CODE}"

PLAN_ID="$(
  curl -fsS "${BASE_URL}/admin/billing/plans" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c '
import json, sys
plans = json.load(sys.stdin)
target = sys.argv[1]
for item in plans:
    if item["code"] == target:
        print(item["id"])
        break
' "${PLAN_CODE}"
)"

if [[ -z "${PLAN_ID}" ]]; then
  echo "billing plan not found: ${PLAN_CODE}" >&2
  exit 1
fi

curl -fsS "${BASE_URL}/admin/clients/${CLIENT_ID}/billing-plan" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d "{\"billing_plan_id\":\"${PLAN_ID}\"}" | python3 -m json.tool
