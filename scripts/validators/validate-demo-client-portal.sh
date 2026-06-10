#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

echo "Validating Demo Client Portal..."

if [[ ! -f "${ROOT_DIR}/.local/demo-client.env" ]]; then
    echo "❌ Error: ${ROOT_DIR}/.local/demo-client.env not found. Please run scripts/dev/seed-demo-local.sh first."
    exit 1
fi

BASE_URL="${BASE_URL:-$(default_base_url)}"
PORTAL_URL="${BASE_URL}/client-portal"
API_URL="${BASE_URL}/portal"
RAG_URL="${BASE_URL}/client/rag"

# shellcheck source=/dev/null
source "${ROOT_DIR}/.local/demo-client.env"

echo "Waiting for Portal UI to be ready..."
for i in {1..30}; do
    HTTP_STATUS="$(curl -L -s -o /dev/null -w "%{http_code}" "${PORTAL_URL}/" || echo "000")"
    if [[ "${HTTP_STATUS}" == "200" ]]; then
        break
    fi
    sleep 1
done

if [[ "${HTTP_STATUS}" != "200" ]]; then
    echo "❌ Portal UI failed to load. HTTP ${HTTP_STATUS}"
    exit 1
fi
echo "✅ Portal UI loaded."

echo "Testing /portal/me with Demo API Key..."
DEMO_MODE_VALUE="$(
    curl_base_url "${API_URL}/me" -s -H "Authorization: Bearer ${DEMO_API_KEY}" | jq -r '.demo_mode'
)"
if [[ "${DEMO_MODE_VALUE}" != "true" ]]; then
    echo "❌ Demo mode is not enabled in the backend or API failed. Got demo_mode=${DEMO_MODE_VALUE}"
    echo "   Run scripts/dev/demo-full-local.sh so DEMO_MODE=true is written before docker compose starts."
    exit 1
fi
echo "✅ Demo mode is active."

PLAN_NAME="$(
    curl_base_url "${API_URL}/me" -s -H "Authorization: Bearer ${DEMO_API_KEY}" | jq -r '.plan.name'
)"
echo "✅ Plan name: ${PLAN_NAME}"

echo "Testing Demo Invoice..."
INVOICES_COUNT="$(
    curl_base_url "${API_URL}/invoices" -s -H "Authorization: Bearer ${DEMO_API_KEY}" | jq -r '.invoices | length'
)"
if [[ "${INVOICES_COUNT}" -eq 0 ]]; then
    echo "⚠️ Warning: No invoices found for demo client."
else
    echo "✅ Found ${INVOICES_COUNT} invoice(s)."
fi

echo "Testing Demo RAG..."
RAG_DOCS="$(
    curl_base_url "${RAG_URL}/documents" -s -H "Authorization: Bearer ${DEMO_API_KEY}" | jq -r '.data | length'
)"
if [[ "${RAG_DOCS}" -eq 0 ]]; then
    echo "⚠️ Warning: No RAG documents found for demo client."
else
    echo "✅ Found ${RAG_DOCS} RAG document(s)."
fi

echo "Testing Playground (test-chat)..."
CHAT_RESPONSE="$(curl_base_url "${API_URL}/test-chat" -s -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${DEMO_API_KEY}" \
     -d '{"prompt": "Test from validate-demo-client-portal.sh", "max_tokens": 10}')"

CHAT_TEXT="$(echo "${CHAT_RESPONSE}" | jq -r '.text // empty')"
if [[ -z "${CHAT_TEXT}" ]]; then
    echo "❌ Chat test failed. Response: ${CHAT_RESPONSE}"
else
    echo "✅ Chat test passed. Response length: ${#CHAT_TEXT}"
fi

echo "------------------------------------------------------"
echo "✅ Validation script completed."
echo "Demo Portal URL: ${PORTAL_URL}/#apiKey=${DEMO_API_KEY}"
echo "Full API Key is in .local/demo-client.env"
echo "------------------------------------------------------"
