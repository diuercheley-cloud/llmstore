#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

log_section "localhost mode validation"

# 1. Check required variables
log_step "Checking required environment variables"

if [ "${LOCALHOST_MODE:-}" != "true" ]; then
  log_error "LOCALHOST_MODE is not set to true. Current: ${LOCALHOST_MODE:-undefined}"
  exit 1
fi
log_ok "LOCALHOST_MODE is true"

# 2. Check docker compose config
log_step "Validating Docker Compose configuration"
log_command "docker compose config"
if (cd "$ROOT_DIR" && dc config > /dev/null 2>&1); then
  log_ok "Docker Compose configuration is valid"
else
  log_error "Docker Compose configuration is invalid"
  exit 1
fi

BASE_URL="${BASE_URL:-$(default_base_url)}"
log_info "Using BASE_URL: ${BASE_URL}"

# 3. Check Health & Ready endpoints
log_step "Checking Health & Ready endpoints"
if curl_base_url "${BASE_URL}/health" -fsS | grep -q "status"; then
  log_curl_mode "${BASE_URL}/health"
  log_ok "Health endpoint returned status"
else
  log_error "Health endpoint failed or returned invalid data"
  exit 1
fi

if curl_base_url "${BASE_URL}/ready" -fsS | grep -q "ready"; then
  log_curl_mode "${BASE_URL}/ready"
  log_ok "Ready endpoint returned ready"
else
  log_error "Ready endpoint failed or returned invalid data"
  exit 1
fi

# 4. Check v1/models
log_step "Checking /v1/models"
HTTP_CODE=$(curl_base_url "$BASE_URL/v1/models" -s -o /dev/null -w "%{http_code}")
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "401" ]; then
  log_curl_mode "${BASE_URL}/v1/models"
  log_ok "/v1/models exists (HTTP $HTTP_CODE)"
else
  log_error "/v1/models returned HTTP $HTTP_CODE"
  exit 1
fi

# 5. Check UI access (landing page, pricing, signup, docs)
log_step "Checking UI pages"
PAGES=("/" "/pricing" "/signup" "/docs")
for page in "${PAGES[@]}"; do
  if curl_base_url "${BASE_URL}${page}" -fsS | grep -q "<html"; then
    log_curl_mode "${BASE_URL}${page}"
    log_ok "Page ${page} is accessible and contains HTML"
  else
    log_error "Page ${page} is not accessible or does not contain HTML"
    exit 1
  fi
done

# 6. Check CORS basic
log_step "Checking CORS for localhost"
CORS_ORIGIN="http://localhost:3000"
CORS_RESPONSE=$(curl_base_url "$BASE_URL/v1/chat/completions" -s -I -X OPTIONS -H "Origin: $CORS_ORIGIN" -H "Access-Control-Request-Method: POST")
if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin: $CORS_ORIGIN"; then
  log_curl_mode "${BASE_URL}/v1/chat/completions"
  log_ok "CORS validation passed for $CORS_ORIGIN"
else
  log_error "CORS validation failed for $CORS_ORIGIN"
  log_info "Response headers: $(echo "$CORS_RESPONSE" | tr '\r\n' ' ')"
  exit 1
fi

# 7. Check public links (should not point to external domain if in localhost mode)
log_step "Checking public links in API response"
RANDOM_NAME="test-client-$(date +%s)"
SIGNUP_RESPONSE=$(curl_base_url "$BASE_URL/public/signup" -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"full_name\": \"$RANDOM_NAME\", \"email\": \"$RANDOM_NAME@example.com\", \"plan_code\": \"free\"}")

if echo "$SIGNUP_RESPONSE" | grep -q "http://localhost" || echo "$SIGNUP_RESPONSE" | grep -q "public signup disabled"; then
  log_curl_mode "${BASE_URL}/public/signup"
  log_ok "Public links validation passed"
else
  log_error "Public links do not point to localhost"
  log_info "Response: ${SIGNUP_RESPONSE}"
  exit 1
fi

log_ok "Localhost mode validation completed successfully!"
