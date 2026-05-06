#!/bin/bash
set -e

# Configuration
ADMIN_TOKEN="${ADMIN_TOKEN:-admin-token-123}"
BASE_URL="${BASE_URL:-http://localhost:18080/admin}"
CURL_OPTS="-s --fail"

echo "=== Validating Admin Lab Endpoints (Local) ==="

# Check connectivity
echo "Checking connectivity to $BASE_URL..."
if ! curl -s --connect-timeout 2 "$BASE_URL/health/deep" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null; then
    echo "ERROR: Could not connect to Admin API at $BASE_URL"
    echo "Make sure the server is running (e.g., make dev or uvicorn app.main:app)"
    exit 1
fi

# 1. List models
echo "1. Testing GET /models..."
RESPONSE=$(curl -s -w "%{http_code}" -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/models")
HTTP_STATUS="${RESPONSE: -3}"
MODELS_JSON="${RESPONSE::-3}"

if [ "$HTTP_STATUS" != "200" ]; then
    echo "   ERROR: GET /models returned HTTP $HTTP_STATUS"
    echo "   Response: $MODELS_JSON"
    echo "   Tip: Check if ADMIN_TOKEN matches the one in your .env file."
    exit 1
fi

COUNT=$(echo $MODELS_JSON | jq '.registry | length' 2>/dev/null || echo "0")
echo "   OK: Found $COUNT models"

# 2. List backends
echo "2. Testing GET /backends..."
BACKENDS_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/backends")
B_COUNT=$(echo $BACKENDS_JSON | jq '. | length')
echo "   OK: Found $B_COUNT backends"

# 3. List model files
echo "3. Testing GET /models/files..."
FILES_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/models/files")
F_COUNT=$(echo $FILES_JSON | jq '.files | length')
echo "   OK: Found $F_COUNT GGUF files"

# 4. System health
echo "4. Testing GET /health/deep..."
HEALTH_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/health/deep")
STATUS=$(echo $HEALTH_JSON | jq -r '.status')
echo "   OK: Status is $STATUS"

# 5. Test model mock creation
echo "5. Testing model lifecycle..."
TEST_MODEL_ID="test-mock-$(date +%s)"
CREATE_JSON=$(curl $CURL_OPTS -X POST "$BASE_URL/models" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"display_name\": \"Test Mock Model\",
    \"model_id\": \"$TEST_MODEL_ID\",
    \"provider\": \"llama.cpp\",
    \"model_file\": \"test.gguf\",
    \"is_active\": false
  }")
MODEL_UUID=$(echo $CREATE_JSON | jq -r '.id')
echo "   Created model: $MODEL_UUID"

# Enable
curl $CURL_OPTS -X POST "$BASE_URL/models/$MODEL_UUID/enable" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
echo "   Enabled model"

# Disable
curl $CURL_OPTS -X POST "$BASE_URL/models/$MODEL_UUID/disable" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
echo "   Disabled model"

# Remove
curl $CURL_OPTS -X DELETE "$BASE_URL/models/$MODEL_UUID" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"confirm_route_removal\": true, \"mode\": \"hard\"}" > /dev/null
echo "   Removed model"

echo "=== Admin Lab Validation Completed Successfully ==="

