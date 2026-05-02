#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  printf 'ADMIN_TOKEN is required.\n' >&2
  exit 1
fi

CLIENT_NAME="fin-flow-$(date +%s)"

echo "--- Admin Lab Financial Flow Test ---"

json_get() {
  python3 - "$1" <<'PY'
import json,sys
print(eval(sys.argv[1], {"__builtins__": {}}, {"data": json.load(sys.stdin)}))
PY
}

echo "1. Loading basic plan..."
PLANS_JSON="$(curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/plans")"
BASIC_PLAN_ID="$(printf '%s' "${PLANS_JSON}" | python3 -c 'import json,sys; plans=json.load(sys.stdin); plan=next((p for p in plans if p["code"]=="basic"), None); assert plan, "basic plan not found"; print(plan["id"])')"
echo "OK: basic=${BASIC_PLAN_ID}"

echo "2. Creating client..."
CLIENT_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"name\":\"${CLIENT_NAME}\",\"billing_plan_id\":\"${BASIC_PLAN_ID}\"}" "${BASE_URL}/admin/clients")"
CLIENT_ID="$(printf '%s' "${CLIENT_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
echo "OK: client=${CLIENT_ID}"

echo "3. Creating API key..."
KEY_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"flow-key\"}" "${BASE_URL}/admin/api-keys")"
API_KEY="$(printf '%s' "${KEY_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["api_key"])')"
echo "OK: API key created"

echo "4. Calling /v1/account..."
ACCOUNT_JSON="$(curl -fsS -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/v1/account")"
ACCOUNT_PLAN="$(printf '%s' "${ACCOUNT_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan"]["code"])')"
[[ "${ACCOUNT_PLAN}" == "basic" ]] || { echo "FAIL: expected basic plan, got ${ACCOUNT_PLAN}"; exit 1; }
echo "OK: account plan is basic"

echo "5. Calling /v1/chat/completions..."
CHAT_JSON="$(curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth/gemma-4-E4B-it-GGUF","messages":[{"role":"user","content":"Responda com uma frase curta: o fluxo financeiro está funcional?"}],"max_tokens":64,"stream":false}')"
CHAT_CONTENT="$(printf '%s' "${CHAT_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])')"
[[ -n "${CHAT_CONTENT}" ]] || { echo "FAIL: empty chat content"; exit 1; }
echo "OK: chat responded"

echo "6. Generating invoice..."
INV_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"force\":true}" "${BASE_URL}/admin/billing/invoices/generate")"
INVOICE_ID="$(printf '%s' "${INV_JSON}" | python3 -c 'import json,sys; data=json.load(sys.stdin); invoice=(data["created"] or data["updated"])[0]; print(invoice["id"])')"
echo "OK: invoice=${INVOICE_ID}"

echo "7. Marking invoice paid..."
curl -fsS -X PATCH -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d '{"payment_method":"script-test"}' "${BASE_URL}/admin/billing/invoices/${INVOICE_ID}/mark-paid" > /dev/null
echo "OK: invoice paid"

echo "8. Validating active billing status..."
CLIENTS_JSON="$(curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/clients")"
STATUS="$(printf '%s' "${CLIENTS_JSON}" | python3 -c 'import json,sys; clients=json.load(sys.stdin); target=next(c for c in clients if c["name"].startswith("fin-flow-")); print(target["billing_status"])')"
[[ "${STATUS}" == "active" ]] || { echo "FAIL: expected active, got ${STATUS}"; exit 1; }
echo "OK: client billing is active"

echo "--- Admin Lab Financial Flow Test PASSED ---"
