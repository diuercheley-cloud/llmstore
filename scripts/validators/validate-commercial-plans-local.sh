#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

echo "Validating commercial plans at ${BASE_URL}..."

PLANS_JSON="$(curl_base_url "${BASE_URL}/admin/billing/plans" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")"
PUBLIC_JSON="$(curl_base_url "${BASE_URL}/public/plans" -fsS)"

require_plan() {
  local code="$1"
  if ! printf '%s' "${PLANS_JSON}" | python3 -c "import json, sys; plans=json.load(sys.stdin); raise SystemExit(0 if any(p.get('code') == '${code}' for p in plans) else 1)"; then
    echo "ERROR: Plan ${code} not found in admin billing plans"
    exit 1
  fi
  echo "Plan ${code} found."
}

plan_field() {
  local code="$1"
  local field="$2"
  printf '%s' "${PLANS_JSON}" | python3 -c "import json, sys; plans=json.load(sys.stdin); plan=next(p for p in plans if p.get('code') == '${code}'); print(plan.get('${field}'))"
}

require_plan "free"
require_plan "basic"
require_plan "pro"

if printf '%s' "${PLANS_JSON}" | python3 -c "import json, sys; plans=json.load(sys.stdin); raise SystemExit(0 if any(p.get('code') in {'enterprise', 'enterprise-local'} for p in plans) else 1)"; then
  echo "Enterprise tier found."
else
  echo "ERROR: No enterprise tier found"
  exit 1
fi

echo "Checking free plan gates..."
if [[ "$(plan_field free rag_enabled)" != "True" ]]; then
  echo "ERROR: Free plan should expose limited RAG in this release"
  exit 1
fi
if [[ "$(plan_field free requests_per_day)" != "100" ]]; then
  echo "ERROR: Free plan requests_per_day should be 100"
  exit 1
fi
echo "Free plan gates validated."

echo "Checking basic/pro upgrades..."
if [[ "$(plan_field basic allow_streaming)" != "True" ]]; then
  echo "ERROR: Basic plan should allow streaming"
  exit 1
fi
if [[ "$(plan_field pro export_enabled)" != "True" ]]; then
  echo "ERROR: Pro plan should allow export"
  exit 1
fi
echo "Basic and pro gates validated."

echo "Checking public pricing plans..."
if ! printf '%s' "${PUBLIC_JSON}" | python3 -c "import json, sys; data=json.load(sys.stdin); plans=data.get('plans', []); required={'free','basic','pro'}; present={p.get('code') for p in plans}; raise SystemExit(0 if required.issubset(present) else 1)"; then
  echo "ERROR: Public plans payload is missing one of free/basic/pro"
  exit 1
fi
echo "Public pricing plans validated."

echo "Commercial plans validation PASSED."
