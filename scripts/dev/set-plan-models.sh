#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

PLAN_CODE="${1:?usage: ./scripts/dev/set-plan-models.sh PLAN_CODE MODEL[,MODEL...]}"
MODELS_CSV="${2:?usage: ./scripts/dev/set-plan-models.sh PLAN_CODE MODEL[,MODEL...]}"

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

PAYLOAD="$(
python3 -c '
import json, sys
models = [item.strip() for item in sys.argv[1].split(",") if item.strip()]
print(json.dumps({"allowed_models": models}))
' "${MODELS_CSV}"
)"

curl -fsS "${BASE_URL}/admin/billing/plans/${PLAN_ID}/models" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d "${PAYLOAD}" | python3 -m json.tool
