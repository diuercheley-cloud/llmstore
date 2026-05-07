#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

PLAN_CODE="${1:?usage: ./scripts/create-plan.sh CODE NAME [RPM] [DAILY] [MONTHLY] [MAX_TOKENS] [ALLOW_STREAMING] [DESCRIPTION]}"
PLAN_NAME="${2:?usage: ./scripts/create-plan.sh CODE NAME [RPM] [DAILY] [MONTHLY] [MAX_TOKENS] [ALLOW_STREAMING] [DESCRIPTION]}"
PLAN_RPM="${3:-10}"
PLAN_DAILY="${4:-50000}"
PLAN_WEEKLY="${5:-200000}"
PLAN_MONTHLY="${6:-500000}"
PLAN_MAX_TOKENS="${7:-512}"
PLAN_ALLOW_STREAMING="${8:-true}"
PLAN_DESCRIPTION="${9:-plan created by script}"

curl -fsS "${BASE_URL}/admin/billing/plans" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"code\": \"${PLAN_CODE}\",
    \"name\": \"${PLAN_NAME}\",
    \"description\": \"${PLAN_DESCRIPTION}\",
    \"rate_limit_per_minute\": ${PLAN_RPM},
    \"daily_token_quota\": ${PLAN_DAILY},
    \"weekly_token_quota\": ${PLAN_WEEKLY},
    \"monthly_token_quota\": ${PLAN_MONTHLY},
    \"max_output_tokens\": ${PLAN_MAX_TOKENS},
    \"allow_streaming\": ${PLAN_ALLOW_STREAMING}
  }" | python3 -m json.tool
