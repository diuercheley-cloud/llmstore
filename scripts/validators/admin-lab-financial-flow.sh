#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
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
import ast
import json
import sys
import operator

ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
}

data = json.load(sys.stdin)

def safe_get(node):
    if isinstance(node, ast.Expression):
        return safe_get(node.body)
    if isinstance(node, ast.Subscript):
        return safe_get(node.value)[safe_get(node.slice)]
    if isinstance(node, ast.Index):
        return safe_get(node.value)
    if isinstance(node, ast.Attribute):
        return getattr(safe_get(node.value), node.attr)
    if isinstance(node, ast.Name):
        if node.id == "data":
            return data
        raise ValueError(f"Variable '{node.id}' not allowed")
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return ALLOWED_OPS[type(node.op)](safe_get(node.left), safe_get(node.right))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -safe_get(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +safe_get(node.operand)
    if isinstance(node, ast.List):
        return [safe_get(el) for el in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(safe_get(el) for el in node.elts)
    raise ValueError(f"Unsupported: {type(node).__name__}")

print(safe_get(ast.parse(sys.argv[1], mode="eval")))
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
