#!/usr/bin/env bash
set -e

export DEMO_MODE=true

source "$(dirname "$0")/common.sh"
source "$(dirname "$0")/activate.sh"

echo "Validating Demo Client Portal..."

if [ ! -f "$ROOT_DIR/.local/demo-client.env" ]; then
    echo "❌ Error: $ROOT_DIR/.local/demo-client.env not found. Please run scripts/seed-demo-local.sh first."
    exit 1
fi

source "$ROOT_DIR/.local/demo-client.env"

PORTAL_URL="http://localhost:18080/client-portal"
API_URL="http://localhost:18080/portal"
RAG_URL="http://localhost:18080/client/rag"

echo "Waiting for Portal UI to be ready..."
for i in {1..30}; do
    HTTP_STATUS=$(curl -L -s -o /dev/null -w "%{http_code}" "$PORTAL_URL/" || echo "000")
    if [ "$HTTP_STATUS" == "200" ]; then
        break
    fi
    sleep 1
done

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Portal UI failed to load. HTTP $HTTP_STATUS"
    exit 1
fi
echo "✅ Portal UI loaded."

echo "Testing /portal/me with Demo API Key..."
DEMO_MODE=$(curl -s -H "Authorization: Bearer $DEMO_API_KEY" "$API_URL/me" | jq -r '.demo_mode')
if [ "$DEMO_MODE" != "true" ]; then
    echo "❌ Demo mode is not enabled in the backend or API failed. Got demo_mode=$DEMO_MODE"
    echo "   Ensure DEMO_MODE=true is set in your .env"
    exit 1
fi
echo "✅ Demo mode is active."

PLAN_NAME=$(curl -s -H "Authorization: Bearer $DEMO_API_KEY" "$API_URL/me" | jq -r '.plan.name')
echo "✅ Plan name: $PLAN_NAME"

echo "Testing Demo Invoice..."
INVOICES_COUNT=$(curl -s -H "Authorization: Bearer $DEMO_API_KEY" "$API_URL/invoices" | jq -r '.invoices | length')
if [ "$INVOICES_COUNT" -eq 0 ]; then
    echo "⚠️ Warning: No invoices found for demo client."
else
    echo "✅ Found $INVOICES_COUNT invoice(s)."
fi

echo "Testing Demo RAG..."
RAG_DOCS=$(curl -s -H "Authorization: Bearer $DEMO_API_KEY" "$RAG_URL/documents" | jq -r '.data | length')
if [ "$RAG_DOCS" -eq 0 ]; then
    echo "⚠️ Warning: No RAG documents found for demo client."
else
    echo "✅ Found $RAG_DOCS RAG document(s)."
fi

echo "Testing Playground (test-chat)..."
CHAT_RESPONSE=$(curl -s -H "Content-Type: application/json" \
     -H "Authorization: Bearer $DEMO_API_KEY" \
     -d '{"prompt": "Test from validate-demo-client-portal.sh", "max_tokens": 10}' \
     "$API_URL/test-chat")

CHAT_TEXT=$(echo "$CHAT_RESPONSE" | jq -r '.text // empty')
if [ -z "$CHAT_TEXT" ]; then
    echo "❌ Chat test failed. Response: $CHAT_RESPONSE"
else
    echo "✅ Chat test passed. Response length: ${#CHAT_TEXT}"
fi

echo "------------------------------------------------------"
echo "✅ Validation script completed."
echo "Demo Portal URL: $PORTAL_URL/#apiKey=$DEMO_API_KEY"
echo "Full API Key is in .local/demo-client.env"
echo "------------------------------------------------------"
