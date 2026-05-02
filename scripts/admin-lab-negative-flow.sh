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

CLIENT_NAME="neg-flow-$(date +%s)"

echo "--- Admin Lab Negative Flow Test ---"

echo "1. Wrong admin token..."
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -H "X-Admin-Token: wrong-token" "${BASE_URL}/admin/clients" || true)"
[[ "${HTTP_CODE}" == "401" ]] || { echo "FAIL: expected 401, got ${HTTP_CODE}"; exit 1; }
echo "OK: wrong admin token blocked"

echo "2. Invalid API key..."
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer sk-invalid" "${BASE_URL}/v1/models" || true)"
[[ "${HTTP_CODE}" == "401" ]] || { echo "FAIL: expected 401, got ${HTTP_CODE}"; exit 1; }
echo "OK: invalid API key blocked"

echo "3. Loading free plan..."
BASIC_JSON="$(curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/plans")"
read -r FREE_PLAN_ID FREE_MAX_OUTPUT <<EOF
$(printf '%s' "${BASIC_JSON}" | python3 -c 'import json,sys; plans=json.load(sys.stdin); plan=next(p for p in plans if p["code"]=="free"); print(plan["id"], plan["max_output_tokens"])')
EOF

echo "4. Creating free-plan client and key..."
CLIENT_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"name\":\"${CLIENT_NAME}\",\"billing_plan_id\":\"${FREE_PLAN_ID}\"}" "${BASE_URL}/admin/clients")"
CLIENT_ID="$(printf '%s' "${CLIENT_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
KEY_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"neg-key\"}" "${BASE_URL}/admin/api-keys")"
API_KEY="$(printf '%s' "${KEY_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["api_key"])')"
echo "OK: client and key created"

echo "5. Streaming blocked on free..."
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth/gemma-4-E4B-it-GGUF","messages":[{"role":"user","content":"teste"}],"max_tokens":32,"stream":true}' || true)"
[[ "${HTTP_CODE}" == "403" || "${HTTP_CODE}" == "400" ]] || { echo "FAIL: expected 400/403 for free streaming, got ${HTTP_CODE}"; exit 1; }
echo "OK: free plan streaming blocked"

echo "6. max_tokens blocked..."
TOO_MUCH=$((FREE_MAX_OUTPUT + 50))
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"unsloth/gemma-4-E4B-it-GGUF\",\"messages\":[{\"role\":\"user\",\"content\":\"teste\"}],\"max_tokens\":${TOO_MUCH},\"stream\":false}" || true)"
[[ "${HTTP_CODE}" == "400" ]] || { echo "FAIL: expected 400 for max_tokens, got ${HTTP_CODE}"; exit 1; }
echo "OK: max_tokens limit enforced"

echo "7. Suspending client..."
curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/security/clients/${CLIENT_ID}/suspend" > /dev/null
HTTP_CODE="$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth/gemma-4-E4B-it-GGUF","messages":[{"role":"user","content":"teste"}],"max_tokens":32,"stream":false}' || true)"
[[ "${HTTP_CODE}" == "403" ]] || { echo "FAIL: expected 403 for suspended client, got ${HTTP_CODE}"; exit 1; }
echo "OK: suspended client blocked"

echo "--- Admin Lab Negative Flow Test PASSED ---"
