#!/bin/bash
set -e

echo "Starting localhost mode validation..."

# Get the project root directory (one level up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Check required variables
echo "Checking required environment variables..."

# Try to load environment variables from potential files in the root directory
for ENV_FILE in "$ROOT_DIR/$STACK_ENV_FILE" "$ROOT_DIR/.env.local" "$ROOT_DIR/.env"; do
  if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    echo "Loading variables from $ENV_FILE"
    # Filter comments and empty lines, then export
    while IFS='=' read -r key value; do
      # Skip comments and empty lines
      [[ "$key" =~ ^#.*$ ]] && continue
      [[ -z "$key" ]] && continue
      # Trim whitespace and handle potential quotes
      key=$(echo "$key" | xargs)
      value=$(echo "$value" | xargs)
      export "$key=$value"
    done < "$ENV_FILE"
    break # Stop after finding the first valid env file
  fi
done

if [ "$LOCALHOST_MODE" != "true" ]; then
  echo "Error: LOCALHOST_MODE is not set to true in environment, .env.local, or .env file."
  echo "Current directory: $(pwd)"
  echo "Root directory: $ROOT_DIR"
  exit 1
fi

# 2. Check docker compose config
echo "Validating Docker Compose configuration..."
(cd "$ROOT_DIR" && docker compose config > /dev/null)

PORT=${HOST_PORT:-18080}
BASE_URL="http://localhost:$PORT"

echo "Using BASE_URL: $BASE_URL"

# 3. Check Health & Ready endpoints
echo "Checking Health endpoint..."
curl -fsS "$BASE_URL/health" | grep -q "status"

echo "Checking Ready endpoint..."
curl -fsS "$BASE_URL/ready" | grep -q "ready"

# 4. Check v1/models
echo "Checking /v1/models..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/v1/models")
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "401" ]; then
  echo "/v1/models exists (HTTP $HTTP_CODE)"
else
  echo "Error: /v1/models returned HTTP $HTTP_CODE"
  exit 1
fi

# 5. Check UI access (landing page, pricing, signup, docs)
echo "Checking UI pages..."
curl -fsS "$BASE_URL/" | grep -q "<html"
curl -fsS "$BASE_URL/pricing" | grep -q "<html"
curl -fsS "$BASE_URL/signup" | grep -q "<html"
curl -fsS "$BASE_URL/docs" | grep -q "<html"

# 6. Check CORS basic
echo "Checking CORS for localhost..."
CORS_ORIGIN="http://localhost:3000"
CORS_RESPONSE=$(curl -s -I -X OPTIONS -H "Origin: $CORS_ORIGIN" -H "Access-Control-Request-Method: POST" "$BASE_URL/v1/chat/completions")
if echo "$CORS_RESPONSE" | grep -q "access-control-allow-origin: $CORS_ORIGIN" || echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin: $CORS_ORIGIN"; then
  echo "CORS validation passed for $CORS_ORIGIN"
else
  echo "Error: CORS validation failed for $CORS_ORIGIN"
  echo "Response headers:"
  echo "$CORS_RESPONSE"
  exit 1
fi

# 7. Check public links (should not point to external domain if in localhost mode)
echo "Checking public links in API response..."
# Use a random name to avoid conflicts if run multiple times
RANDOM_NAME="test-client-$(date +%s)"
SIGNUP_RESPONSE=$(curl -s -X POST "$BASE_URL/public/signup" \
  -H "Content-Type: application/json" \
  -d "{\"full_name\": \"$RANDOM_NAME\", \"email\": \"$RANDOM_NAME@example.com\", \"plan_code\": \"free\"}")

if echo "$SIGNUP_RESPONSE" | grep -q "http://localhost"; then
  echo "Public links validation passed (contains http://localhost)"
else
  echo "Error: Public links do not point to localhost."
  echo "Response: $SIGNUP_RESPONSE"
  exit 1
fi

echo "Localhost mode validation completed successfully!"
