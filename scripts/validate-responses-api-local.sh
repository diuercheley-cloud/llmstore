#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
MODEL="${MODEL:-default}"

# Ensure we have an API key
echo "Resolving API Key..."
API_KEY="$(require_api_key "${BASE_URL}" "responses-validation")"
export API_KEY

echo "--- 1. Validating Auth ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/v1/responses" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"${MODEL}\", \"input\": \"hi\"}")
if [ "$HTTP_CODE" != "401" ]; then
  echo "FAILED: Auth should be required (expected 401, got $HTTP_CODE)"
  exit 1
fi
echo "PASSED: Auth required"

echo "--- 2. Validating basic /v1/responses (string input) ---"
RESPONSE=$(curl_base_url "${BASE_URL}/v1/responses" -s -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"input\": \"Responda apenas OK.\",
    \"instructions\": \"Seja direto.\",
    \"temperature\": 0.1
  }")

if ! echo "$RESPONSE" | grep -q "\"output_text\""; then
  echo "FAILED: Response missing output_text"
  echo "$RESPONSE"
  exit 1
fi
if ! echo "$RESPONSE" | grep -q "\"created_at\""; then
  echo "FAILED: Response missing created_at"
  echo "$RESPONSE"
  exit 1
fi
if ! echo "$RESPONSE" | grep -q "\"usage\""; then
  echo "FAILED: Response missing usage"
  echo "$RESPONSE"
  exit 1
fi
echo "PASSED: Basic /v1/responses"

echo "--- 3. Validating array input and instructions mapping ---"
RESPONSE=$(curl_base_url "${BASE_URL}/v1/responses" -s -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"instructions\": \"Responda em uma linha.\",
    \"input\": [
      \"Contexto curto.\",
      {\"role\": \"user\", \"content\": \"Diga OK.\"}
    ]
  }")

if ! echo "$RESPONSE" | grep -q "\"output\""; then
  echo "FAILED: Response missing output for array input"
  echo "$RESPONSE"
  exit 1
fi
echo "PASSED: Array input"

echo "--- 3. Validating tools (should return 501) ---"
TOOLS_RESPONSE=$(curl_base_url "${BASE_URL}/v1/responses" -s -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"input\": \"hi\",
    \"tools\": [{\"type\": \"function\", \"function\": {\"name\": \"test\"}}]
  }")
HTTP_CODE=$(printf '%s' "${TOOLS_RESPONSE}" | python3 -c 'import json,sys; print(501 if json.load(sys.stdin).get("error", {}).get("code") == "responses_tools_unsupported" else 0)')
if [ "$HTTP_CODE" != "501" ]; then
  echo "FAILED: Tools should return structured 501"
  echo "$TOOLS_RESPONSE"
  exit 1
fi
echo "PASSED: Tools 501"

echo "--- 4. Validating stream (should return 501) ---"
STREAM_RESPONSE=$(curl_base_url "${BASE_URL}/v1/responses" -s -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"input\": \"hi\",
    \"stream\": true
  }")
HTTP_CODE=$(printf '%s' "${STREAM_RESPONSE}" | python3 -c 'import json,sys; print(501 if json.load(sys.stdin).get("error", {}).get("code") == "responses_streaming" else 0)')
if [ "$HTTP_CODE" != "501" ]; then
  echo "FAILED: Stream should return structured 501"
  echo "$STREAM_RESPONSE"
  exit 1
fi
echo "PASSED: Stream 501"

echo "--- 5. Validating suspended client ---"
# Get demo client id
DEMO_CLIENT_ID=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/clients" | python3 -c 'import json, sys; print(next((c["id"] for c in json.load(sys.stdin) if c["name"] == "demo-client"), ""))')

if [ -n "$DEMO_CLIENT_ID" ]; then
  echo "Suspending client $DEMO_CLIENT_ID (billing)..."
  curl -s -X PATCH -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
    -d '{"billing_status": "suspended"}' "${BASE_URL}/admin/clients/$DEMO_CLIENT_ID" > /dev/null

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}/v1/responses" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${MODEL}\", \"input\": \"hi\"}")

  echo "Reactivating client $DEMO_CLIENT_ID..."
  curl -s -X PATCH -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
    -d '{"billing_status": "active"}' "${BASE_URL}/admin/clients/$DEMO_CLIENT_ID" > /dev/null

  if [ "$HTTP_CODE" != "402" ]; then
    echo "FAILED: Suspended client should return 402 (got $HTTP_CODE)"
    exit 1
  fi
  echo "PASSED: Suspended client blocked with 402"
else

  echo "SKIPPING: Could not find CLIENT_ID to test suspension"
fi

echo "--- 6. Validating examples ---"
chmod +x "${SCRIPT_DIR}/../examples/curl/responses.sh"
BASE_URL="${BASE_URL}" CLIENT_API_KEY="${API_KEY}" MODEL="${MODEL}" "${SCRIPT_DIR}/../examples/curl/responses.sh" > /tmp/responses-curl-example.out
if ! grep -q '"output_text"' /tmp/responses-curl-example.out; then
  echo "FAILED: curl example did not produce output_text"
  cat /tmp/responses-curl-example.out
  exit 1
fi

BASE_URL="${BASE_URL}" CLIENT_API_KEY="${API_KEY}" .venv/bin/python "${SCRIPT_DIR}/../examples/python/responses.py" > /tmp/responses-python-example.out
if ! grep -q '"output_text"' /tmp/responses-python-example.out; then
  echo "FAILED: python example did not produce output_text"
  cat /tmp/responses-python-example.out
  exit 1
fi

if command -v node >/dev/null 2>&1; then
  BASE_URL="${BASE_URL}" CLIENT_API_KEY="${API_KEY}" node "${SCRIPT_DIR}/../examples/node/responses.js" > /tmp/responses-node-example.out
  if ! grep -q '"output_text"' /tmp/responses-node-example.out; then
    echo "FAILED: node example did not produce output_text"
    cat /tmp/responses-node-example.out
    exit 1
  fi
else
  echo "SKIPPING: node not installed; node example not executed"
fi
echo "PASSED: Examples"

echo "--- All /v1/responses validations PASSED ---"
