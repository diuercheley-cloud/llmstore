source scripts/common.sh
init_stack_env

BASIC_JSON="$(curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/plans")"
FREE_PLAN_ID="$(printf '%s' "${BASIC_JSON}" | python3 -c 'import json,sys; plans=json.load(sys.stdin); plan=next(p for p in plans if p["code"]=="free"); print(plan["id"])')"

CLIENT_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -d "{\"name\":\"test-429-2\",\"billing_plan_id\":\"${FREE_PLAN_ID}\"}" "http://localhost:18080/admin/clients")"
CLIENT_ID="$(printf '%s' "${CLIENT_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
KEY_JSON="$(curl -fsS -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"neg-key\"}" "http://localhost:18080/admin/api-keys")"
API_KEY="$(printf '%s' "${KEY_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["api_key"])')"

curl -sS -D - "http://localhost:18080/v1/chat/completions" -H "Authorization: Bearer ${API_KEY}" -H "Content-Type: application/json" -d "{\"model\":\"unsloth/gemma-4-E4B-it-GGUF\",\"messages\":[{\"role\":\"user\",\"content\":\"teste\"}],\"max_tokens\":33000,\"stream\":false}"
