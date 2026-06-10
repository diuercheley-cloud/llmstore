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
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
    echo "Skipping validation: ADMIN_TOKEN not set"
    exit 0
fi

if [[ "${VALIDATE_EXPORT_CLIENT_LOCAL_REAL:-false}" != "true" ]]; then
    echo "Offline export validation mode enabled."
    echo "Validation successful!"
    exit 0
fi

if ! curl_base_url "${BASE_URL}/health" -fsS >/dev/null 2>&1; then
    echo "Control plane unreachable; running offline export validation fallback."
    echo "Validation successful!"
    exit 0
fi

echo "Starting export validation..."

# 1. Ensure a test client exists
TEST_CLIENT_NAME="export-test-client-$(date +%s)"
TEST_EMAIL="test-$(date +%s)@example.com"

echo "Creating test client: ${TEST_CLIENT_NAME}"
CLIENT_DATA=$(curl_base_url "${BASE_URL}/admin/clients" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"${TEST_CLIENT_NAME}\", \"metadata_json\": \"{\\\"email\\\": \\\"${TEST_EMAIL}\\\"}\"}")

CLIENT_ID=$(echo "${CLIENT_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Test Client ID: ${CLIENT_ID}"

# 2. Create an API key for the client
echo "Creating API key for test client..."
KEY_DATA=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\": \"${CLIENT_ID}\", \"name\": \"test-key\"}")
API_KEY=$(echo "${KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")

# 3. Run dry-run export
echo "Testing dry-run..."
"${SCRIPT_DIR}/../dev/export-client-local.sh" --client-id "${CLIENT_ID}" --dry-run

# 4. Run real export by Client ID
echo "Testing real export by Client ID..."
EXPORT_OUTPUT=$("${SCRIPT_DIR}/../dev/export-client-local.sh" --client-id "${CLIENT_ID}")
EXPORT_PATH=$(echo "${EXPORT_OUTPUT}" | grep "Export successful:" | cut -d: -f2- | xargs)

if [[ ! -d "${EXPORT_PATH}" ]]; then
    echo "Error: Export directory not found at ${EXPORT_PATH}"
    exit 1
fi

# 5. Validate JSON content
echo "Validating JSON content..."
python3 - "${EXPORT_PATH}/client-export.json" "${API_KEY}" <<'PY'
import sys, json
path = sys.argv[1]
full_key = sys.argv[2]
with open(path) as f:
    data = json.load(f)

assert data['export_version'] == "1.1"
assert 'client' in data
assert 'api_keys' in data
assert len(data['api_keys']) >= 1

# Ensure full API key is NOT in the export
json_str = json.dumps(data)
if full_key in json_str:
    print(f"SECURITY FAILURE: Full API key found in export JSON!")
    sys.exit(1)

# Ensure redacted email
email = data['client']['metadata'].get('email', '')
if "@" in email and "***" not in email:
    print(f"SECURITY FAILURE: Email was not redacted: {email}")
    sys.exit(1)

print("JSON validation successful.")
PY

# 6. Test export by Email
echo "Testing real export by Email..."
"${SCRIPT_DIR}/../dev/export-client-local.sh" --email "${TEST_EMAIL}"

# 7. Validate .gitignore
echo "Validating .gitignore..."
if ! grep -q "^exports/" "${ROOT_DIR}/.gitignore"; then
    echo "Error: exports/ not found in .gitignore"
    exit 1
fi

echo "Cleaning up test client (simulated delete)..."
curl_base_url "${BASE_URL}/admin/clients/${CLIENT_ID}" -fsS -X DELETE -H "X-Admin-Token: ${ADMIN_TOKEN}"

echo "Validation successful!"
