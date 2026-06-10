#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
if [[ -f "/.dockerenv" && "${BASE_URL}" == "http://localhost:${HOST_PORT:-18080}" ]]; then
    BASE_URL="http://host.docker.internal:${HOST_PORT:-18080}"
fi
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

TEST_CLIENT_NAME="delete-test-client-$(date +%s)"

echo "1. Creating test client '${TEST_CLIENT_NAME}'..."
CREATE_OUTPUT=$("${SCRIPT_DIR}/../dev/create-client.sh" "${TEST_CLIENT_NAME}" "Temporary client for deletion validation")
CLIENT_ID=$(echo "${CREATE_OUTPUT}" | grep client_id | cut -d= -f2)
API_KEY=$(echo "${CREATE_OUTPUT}" | grep api_key | cut -d= -f2)

echo "Client ID: ${CLIENT_ID}"

echo "2. Verifying API key works..."
HEALTH_CHECK=$(curl -s -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/v1/models" || echo "FAILED")
if [[ "${HEALTH_CHECK}" == "FAILED" ]]; then
    echo "Error: API key not working for new client"
    exit 1
fi
echo "API key works."

echo "3. Testing Dry Run..."
"${SCRIPT_DIR}/../dev/delete-client-local.sh" --client-id "${CLIENT_ID}" --dry-run

echo "4. Running Export..."
"${SCRIPT_DIR}/../dev/export-client-local.sh" --client-id "${CLIENT_ID}" --include-rag-files --include-tts-files

echo "5. Performing Secure Delete (with --require-export)..."
# Should use existing export
"${SCRIPT_DIR}/../dev/delete-client-local.sh" --client-id "${CLIENT_ID}" --yes --require-export --delete-rag-files --delete-tts-files --delete-invoices

echo "6. Verifying client is gone/inactive..."
# Try to use API key again
echo "Verifying API key is revoked..."
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/v1/models")
if [[ "${STATUS_CODE}" == "401" || "${STATUS_CODE}" == "403" ]]; then
    echo "API key correctly revoked (Status: ${STATUS_CODE})."
else
    echo "Error: API key still works or returned unexpected status: ${STATUS_CODE}"
    exit 1
fi

echo "Verifying client not in list..."
CLIENT_LIST="$(curl_base_url "${BASE_URL}/admin/clients" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")"
if echo "${CLIENT_LIST}" | grep -q "${CLIENT_ID}"; then
    echo "Error: Client ID still appears in active list"
    exit 1
fi
echo "Client confirmed gone from active list."

echo "7. Safety Checks..."
echo "Verifying demo-client still exists..."
if ! echo "${CLIENT_LIST}" | grep -q "demo-client"; then
    echo "Error: demo-client was accidentally deleted!"
    exit 1
fi
echo "demo-client safe."

echo "Verifying models directory is untouched..."
if [[ ! -d "${ROOT_DIR}/models" ]]; then
    echo "Error: models directory missing!"
    exit 1
fi
echo "models/ directory preserved."

echo "8. Verifying report generation..."
LATEST_REPORT=$(ls -dt "${ROOT_DIR}/artifacts/client-deletions/"* | head -1 || true)
if [[ -z "${LATEST_REPORT}" ]]; then
    echo "Error: No deletion report found"
    exit 1
fi
echo "Report found at ${LATEST_REPORT}"

echo "Validation successful!"
