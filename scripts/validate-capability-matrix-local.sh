#!/usr/bin/env bash

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/lib/validation-logging.sh"
init_stack_env

# Configuration
URL="${BASE_URL:-$(default_base_url)}/admin/capabilities"

log_section "Capability Matrix Validation"

# 1. Check if docs/CAPABILITY_MATRIX.md exists
log_step "Checking docs/CAPABILITY_MATRIX.md"
if [ -f "${ROOT_DIR}/docs/CAPABILITY_MATRIX.md" ]; then
    log_ok "docs/CAPABILITY_MATRIX.md exists"
else
    log_error "docs/CAPABILITY_MATRIX.md is missing"
    exit 1
fi

# 2. Check if endpoint exige token
log_step "Verifying admin token requirement"
STATUS_NO_TOKEN=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
if [ "$STATUS_NO_TOKEN" == "401" ] || [ "$STATUS_NO_TOKEN" == "403" ]; then
    log_ok "Endpoint correctly rejected request without token ($STATUS_NO_TOKEN)"
else
    log_warn "Endpoint returned $STATUS_NO_TOKEN without token (expected 401/403)"
fi

# 3. Check endpoint returns valid JSON with mandatory features
log_step "Fetching $URL with admin token"
# Get ADMIN_TOKEN from .env if not set
if [ -z "$ADMIN_TOKEN" ]; then
    ADMIN_TOKEN=$(grep ADMIN_TOKEN "${ROOT_DIR}/.env.local" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi

CONTENT=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$URL")

if [ -n "$CONTENT" ] && ! echo "$CONTENT" | grep -q "404 Not Found" && ! echo "$CONTENT" | grep -q "Internal Server Error"; then
  log_ok "Successfully fetched capabilities"
  
  # Check for mandatory features
  MANDATORY_FEATURES=("/v1/chat/completions" "streaming" "/v1/models" "RAG" "TTS")
  for feature in "${MANDATORY_FEATURES[@]}"; do
    if echo "$CONTENT" | grep -q "\"feature\"[[:space:]]*:[[:space:]]*\"$feature\""; then
      log_ok "Mandatory feature found: $feature"
    else
      log_error "Mandatory feature NOT found: $feature"
      log_info "Content received: $CONTENT"
      exit 1
    fi
  done
  
  # 4. PSP/PIX real marked as not_supported/future
  log_step "Checking PSP/PIX status"
  if echo "$CONTENT" | grep -A 5 "\"feature\"[[:space:]]*:[[:space:]]*\"PSP/PIX real\"" | grep -q "\"status\"[[:space:]]*:[[:space:]]*\"Future\""; then
      log_ok "PSP/PIX correctly marked as Future"
  else
      log_error "PSP/PIX NOT marked as Future"
      exit 1
  fi
  
  # 5. tools marked as partial/unsupported
  log_step "Checking tools status"
  if echo "$CONTENT" | grep -A 5 "\"feature\"[[:space:]]*:[[:space:]]*\"tools/function calling\"" | grep -q "\"status\"[[:space:]]*:[[:space:]]*\"Unsupported\""; then
      log_ok "Tools correctly marked as Unsupported"
  else
      log_error "Tools NOT marked as Unsupported"
      exit 1
  fi

else
  log_error "Failed to fetch capabilities or it's empty: $CONTENT"
  exit 1
fi

log_ok "Capability Matrix validation completed successfully"
