#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

# Configuration
BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token"}

echo "--- Validating Demo Admin Dashboard ---"

# 1. Check if dashboard loads
echo "Checking Admin Dashboard HTML..."
curl_base_url "$BASE_URL/admin-dashboard" -fsS -o /dev/null
echo "✅ Admin Dashboard HTML loads."

# 2. Check /admin/demo/summary
echo "Checking /admin/demo/summary..."
SUMMARY_JSON=$(curl_base_url "$BASE_URL/admin/demo/summary" -fsS -H "X-Admin-Token: $ADMIN_TOKEN")
echo "$SUMMARY_JSON" | jq . > /dev/null
echo "✅ /admin/demo/summary responds with valid JSON."

# 3. Validate demo summary structure
echo "Validating summary structure..."
if ! echo "$SUMMARY_JSON" | jq -e '.demo_enabled == true' > /dev/null; then
    echo "❌ Demo mode is not enabled in /admin/demo/summary."
    echo "   Run scripts/dev/demo-full-local.sh so DEMO_MODE=true is written before docker compose starts."
    exit 1
fi
echo "$SUMMARY_JSON" | jq -e '.demo_client' > /dev/null
echo "$SUMMARY_JSON" | jq -e '.demo_usage' > /dev/null
echo "$SUMMARY_JSON" | jq -e '.demo_billing' > /dev/null
echo "$SUMMARY_JSON" | jq -e '.demo_rag' > /dev/null
echo "$SUMMARY_JSON" | jq -e '.demo_models' > /dev/null
echo "✅ Summary structure is correct."

# 4. Check for API keys exposure
echo "Checking for API key exposure in summary..."
if echo "$SUMMARY_JSON" | grep -q '"api_key": "sk-'; then
    # Some API keys might be there but should be masked or only prefix
    # Requirement: "API keys, somente prefixo"
    # Let's check if any API key has more than 12 characters after sk- (sk- + 8 prefix + ... = ~12-15)
    if echo "$SUMMARY_JSON" | grep -P '"api_key": "sk-[a-zA-Z0-9]{12,}"'; then
        echo "❌ Full API keys detected in summary!"
        exit 1
    fi
fi
echo "✅ No full API keys detected."

# 5. Check other admin endpoints used by dashboard
echo "Checking other admin endpoints..."
curl_base_url "$BASE_URL/admin/usage/summary" -fsS -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
curl_base_url "$BASE_URL/admin/usage/by-client" -fsS -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
curl_base_url "$BASE_URL/admin/models" -fsS -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
curl_base_url "$BASE_URL/admin/rag/usage" -fsS -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
echo "✅ Other admin endpoints are responding."

echo "--- Admin Dashboard Validation Successful ---"
