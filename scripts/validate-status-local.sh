#!/bin/bash
set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting status endpoints validation..."

# Load environment
for ENV_FILE in "$ROOT_DIR/$STACK_ENV_FILE" "$ROOT_DIR/.env.local" "$ROOT_DIR/.env"; do
  if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    echo "Loading variables from $ENV_FILE"
    while IFS='=' read -r key value; do
      [[ "$key" =~ ^#.*$ ]] && continue
      [[ -z "$key" ]] && continue
      export "$(echo "$key" | xargs)=$(echo "$value" | xargs)"
    done < "$ENV_FILE"
    break
  fi
done

PORT=${HOST_PORT:-18080}
BASE_URL="http://localhost:$PORT"
ADMIN_TOKEN=${ADMIN_TOKEN:-"ChangeMe_ProdAdminToken_2026!"}

echo "Using BASE_URL: $BASE_URL"

# 1. Check /health
echo "Checking /health (Minimalist check)..."
HEALTH_RESP=$(curl -fsS "$BASE_URL/health")
echo "$HEALTH_RESP" | grep -q "\"status\":\"ok\""
echo "$HEALTH_RESP" | grep -q "\"process\":\"alive\""

# 2. Check /ready
echo "Checking /ready (Dependency check)..."
READY_RESP=$(curl -s "$BASE_URL/ready")
if echo "$READY_RESP" | grep -q "\"status\":\"ready\""; then
  echo "/ready is OK"
elif echo "$READY_RESP" | grep -q "\"status\":\"not_ready\""; then
  echo "/ready is NOT READY (Expected if some dependencies are offline, but well-formed)"
else
  echo "Error: /ready returned unexpected response: $READY_RESP"
  exit 1
fi

# 3. Check /status
echo "Checking /status (Public summarized check)..."
STATUS_RESP=$(curl -fsS "$BASE_URL/status")
echo "$STATUS_RESP" | grep -q "\"api\":\"online\""
if echo "$STATUS_RESP" | grep -E "key|token|password|secret"; then
  echo "Error: Secrets leaked in /status!"
  exit 1
fi

# 4. Check /admin/status (Exige token)
echo "Checking /admin/status (Detailed check with token)..."
ADMIN_STATUS_RESP=$(curl -fsS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/status")
echo "$ADMIN_STATUS_RESP" | grep -q "\"postgres\""
echo "$ADMIN_STATUS_RESP" | grep -q "\"redis\""
echo "$ADMIN_STATUS_RESP" | grep -q "\"queues\""
echo "$ADMIN_STATUS_RESP" | grep -q "\"inference\""

# 5. Check /admin/status security (Should fail without token)
echo "Checking /admin/status security (Should fail without token)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/status")
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
  echo "Security check passed (Returned $HTTP_CODE)"
else
  echo "Error: /admin/status security check failed (Returned $HTTP_CODE, expected 401/403)"
  exit 1
fi

echo "Status endpoints validation completed successfully!"
