#!/bin/bash
set -e

# Hermetic Preflight Check
bash scripts/legacy/preflight-hermetic.sh || exit 1

BASE_URL=${KLEBER_BASE_URL:-"http://localhost:18080"}
API_KEY=${KLEBER_API_KEY}
MODE=${AGENTIC_READINESS_MODE:-"advisory"} # advisory | release
ALLOW_DEGRADED=${AGENTIC_READINESS_ALLOW_DEGRADED:-"false"}

if [ -z "${API_KEY}" ]; then
    for env_file in .env.local .env; do
        if [ -f "${env_file}" ]; then
            API_KEY=$(grep -E '^ADMIN_TOKEN=' "${env_file}" | head -n1 | cut -d= -f2- || true)
            API_KEY=${API_KEY%\"}
            API_KEY=${API_KEY#\"}
            [ -n "${API_KEY}" ] && break
        fi
    done
fi

echo "----------------------------------------------------------------"
echo "  AGENTIC RUNTIME READINESS CHECK (Mode: $MODE)"
echo "----------------------------------------------------------------"

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo "WARNING: KLEBER_API_KEY is not set. Requests might fail if authentication is required."
fi

# Run readiness check
RESPONSE=$(curl -s -H "X-Admin-Token: $API_KEY" -X GET "$BASE_URL/admin/agents/readiness")

# Check for 404 or other errors
if [[ $(echo "$RESPONSE" | jq -r '.detail' 2>/dev/null) == "Not Found" ]]; then
    echo "ERROR: Readiness endpoint not found (404). Ensure the router is registered and the server is running."
    exit 1
fi

STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null)

if [ "$STATUS" == "null" ] || [ -z "$STATUS" ]; then
    echo "ERROR: Unexpected readiness response."
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo "Timestamp: $(echo "$RESPONSE" | jq -r '.timestamp')"
echo "Status:    $STATUS"
echo "----------------------------------------------------------------"

# Display Checks
echo "Detailed Checks:"
echo "$RESPONSE" | jq -r '.checks[] | "[\(.status | ascii_upcase)] \(.name): \(.value) (\(.message // "OK"))"'

# Display Blockers
BLOCKERS_COUNT=$(echo "$RESPONSE" | jq '.blockers | length' 2>/dev/null || echo 0)
if [ "$BLOCKERS_COUNT" -gt 0 ]; then
    echo ""
    echo "BLOCKERS DETECTED ($BLOCKERS_COUNT):"
    echo "$RESPONSE" | jq -r '.blockers[] | "- \(.)"'
fi

# Display Warnings
WARNINGS_COUNT=$(echo "$RESPONSE" | jq '.warnings | length' 2>/dev/null || echo 0)
if [ "$WARNINGS_COUNT" -gt 0 ]; then
    echo ""
    echo "WARNINGS ($WARNINGS_COUNT):"
    echo "$RESPONSE" | jq -r '.warnings[] | "- \(.)"'
fi

# Display Recommendations
RECS_COUNT=$(echo "$RESPONSE" | jq '.recommendations | length' 2>/dev/null || echo 0)
if [ "$RECS_COUNT" -gt 0 ]; then
    echo ""
    echo "RECOMMENDATIONS:"
    echo "$RESPONSE" | jq -r '.recommendations[] | "- \(.)"'
fi

echo "----------------------------------------------------------------"

if [ "$STATUS" == "ready" ]; then
    echo "✅ Agentic Runtime is ready for production."
    exit 0
elif [ "$STATUS" == "disabled" ]; then
    echo "⚪ Agentic Runtime is disabled (safe default)."
    exit 0
elif [ "$STATUS" == "degraded" ]; then
    if [ "$MODE" == "release" ] && [ "$ALLOW_DEGRADED" != "true" ]; then
        echo "❌ Agentic Runtime is DEGRADED. Blocked in release mode."
        exit 1
    else
        echo "⚠️  Agentic Runtime is degraded. Review warnings."
        exit 0
    fi
elif [ "$STATUS" == "blocked" ]; then
    echo "❌ Agentic Runtime is BLOCKED. Manual intervention required."
    exit 1
else
    echo "❌ Agentic Runtime state is UNKNOWN ($STATUS)."
    exit 1
fi
