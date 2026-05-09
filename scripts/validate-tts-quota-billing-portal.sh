#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

create_client() {
  local client_name="$1"
  local output
  output="$("${SCRIPT_DIR}/create-client.sh" "${client_name}")"
  local client_id
  local api_key
  client_id="$(printf '%s\n' "${output}" | awk -F= '/^client_id=/{print $2}')"
  api_key="$(printf '%s\n' "${output}" | awk -F= '/^api_key=/{print $2}')"
  if [[ -z "${client_id}" || -z "${api_key}" ]]; then
    echo "Failed to parse client creation output for ${client_name}" >&2
    printf '%s\n' "${output}" >&2
    exit 1
  fi
  printf '%s;%s\n' "${client_id}" "${api_key}"
}

echo "=== Starting TTS Hardening Validation ==="

# 1. Setup - Ensure we have clients for different plans
echo "Setting up test clients..."

FREE_CLIENT_NAME="tts_test_free_$(date +%s)"
FREE_CLIENT_DATA="$(create_client "${FREE_CLIENT_NAME}")"
FREE_CLIENT_ID="${FREE_CLIENT_DATA%%;*}"
FREE_KEY="${FREE_CLIENT_DATA##*;}"
"${SCRIPT_DIR}/set-client-plan.sh" "${FREE_CLIENT_ID}" "free" >/dev/null
echo "Free Client Key: $FREE_KEY"

BASIC_CLIENT_NAME="tts_test_basic_$(date +%s)"
BASIC_CLIENT_DATA="$(create_client "${BASIC_CLIENT_NAME}")"
BASIC_CLIENT_ID="${BASIC_CLIENT_DATA%%;*}"
BASIC_KEY="${BASIC_CLIENT_DATA##*;}"
"${SCRIPT_DIR}/set-client-plan.sh" "${BASIC_CLIENT_ID}" "basic" >/dev/null
echo "Basic Client Key: $BASIC_KEY"

# 2. Validate Free client blocked
echo "Validating Free client (TTS disabled) is blocked..."
HTTP_CODE=$(curl_base_url "${BASE_URL}/pocket-tts/tts" -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $FREE_KEY" \
  -F "text=This should be blocked")

if [ "$HTTP_CODE" -eq 403 ]; then
  echo "✅ Free client blocked as expected (403)"
else
  echo "❌ Free client NOT blocked (Status: $HTTP_CODE)"
  exit 1
fi

# 3. Validate Basic client allowed
echo "Validating Basic client (TTS enabled) is allowed..."
HTTP_CODE=$(curl_base_url "${BASE_URL}/pocket-tts/tts" -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $BASIC_KEY" \
  -F "text=This is a test of TTS hardening. It should work.")

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "✅ Basic client allowed as expected (200)"
else
  echo "❌ Basic client NOT allowed (Status: $HTTP_CODE)"
  exit 1
fi

# 4. Validate Quota enforcement (Basic has low quota in my setup: 500 chars per request)
echo "Validating character quota per request..."
BASIC_REQUEST_LIMIT=500
LARGE_TEXT="$(python3 - <<'PY'
print("a" * 501)
PY
)"
HTTP_CODE=$(curl_base_url "${BASE_URL}/pocket-tts/tts" -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $BASIC_KEY" \
  -F "text=$LARGE_TEXT")

if [ "$HTTP_CODE" -eq 413 ]; then
  echo "✅ Large request blocked as expected (413)"
else
  echo "❌ Large request NOT blocked (Status: $HTTP_CODE)"
  exit 1
fi

# 5. Validate Usage Registration
echo "Validating usage registration in Portal/Admin APIs..."
USAGE_DATA=$(curl_base_url "${BASE_URL}/admin/usage/${BASIC_CLIENT_ID}/summary" -s -H "X-Admin-Token: ${ADMIN_TOKEN}")
CHARS_USED=$(echo "$USAGE_DATA" | jq -r ".today.tts_chars_used")

if [ "$CHARS_USED" -gt 0 ]; then
  echo "✅ TTS usage registered: $CHARS_USED chars"
else
  echo "❌ TTS usage NOT registered"
  exit 1
fi

# 6. Validate Invoice Preview includes TTS
echo "Validating Invoice Preview..."
INVOICE_PREVIEW=$(curl_base_url "${BASE_URL}/admin/billing/clients/${BASIC_CLIENT_ID}/invoice/preview" -s -H "X-Admin-Token: ${ADMIN_TOKEN}")
TTS_IN_INVOICE=$(echo "$INVOICE_PREVIEW" | jq -r ".invoice_preview.tts_chars_used")

if [ "$TTS_IN_INVOICE" -gt 0 ]; then
  echo "✅ Invoice preview includes TTS: $TTS_IN_INVOICE chars"
else
  echo "❌ Invoice preview does NOT include TTS"
  exit 1
fi

# 7. Validate Isolation (Client A cannot see Client B audio - though pocket-tts is stateless, we check isolation headers)
# Since pocket-tts is proxied, we ensure Client ID header is passed
# (Internal check, harder to validate via curl without pocket-tts logs access, 
# but we trust the proxy logic added X-Client-ID)

# 8. Clean up
echo "Cleaning up test clients..."
# Add purge logic if available or just leave them for manual inspection if needed

echo "=== TTS Hardening Validation Completed Successfully! ==="
