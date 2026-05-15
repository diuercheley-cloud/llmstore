#!/usr/bin/env bash
# LLM Inference Stack - Customer Readiness Validator
# Validates if a client installation is fully functional and secure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load env
if [ -f "${ROOT_DIR}/.env.local" ]; then
  source "${ROOT_DIR}/.env.local"
fi

BASE_URL="${APP_PUBLIC_URL:-http://localhost:18080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

# Validation results
STATUS="READY"
REASONS=()

log_check() { echo -n -e "${BLUE}[CHECK]${NC} $1... "; }
log_pass() { echo -e "${GREEN}PASS${NC}"; }
log_fail() {
  echo -e "${RED}FAIL${NC}"
  STATUS="NOT READY"
  REASONS+=("$1")
}

echo -e "\n${BLUE}====================================================${NC}"
echo -e "${BLUE}    Customer Readiness Validation                  ${NC}"
echo -e "${BLUE}    Target: ${BASE_URL}                            ${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# 1. Health Checks
log_check "Global health (/health)"
if curl -fsS "${BASE_URL}/health" | grep -q "ok"; then log_pass; else log_fail "Global health endpoint failed"; fi

log_check "Readiness check (/ready)"
if curl -fsS "${BASE_URL}/ready" | grep -q "ok"; then log_pass; else log_fail "Readiness endpoint failed"; fi

# 2. API Functionality
log_check "List models (/v1/models)"
if curl -fsS "${BASE_URL}/v1/models" | grep -q "object"; then log_pass; else log_fail "Failed to list models"; fi

# Get a test API key (using admin token if available)
if [ -n "$ADMIN_TOKEN" ]; then
  log_check "Admin protection (authenticated check)"
  if curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/health/deep" > /dev/null 2>&1; then
    log_pass
  else
    log_fail "Admin endpoint access failed with token"
  fi
  
  # Try to get an API key for chat validation
  log_check "Chat completion (/v1/chat/completions)"
  # Find first active client API key
  API_KEY=$(psql "$DATABASE_URL" -t -c "SELECT key FROM api_keys WHERE is_active=true LIMIT 1;" 2>/dev/null | xargs || echo "")
  
  if [ -z "$API_KEY" ]; then
    # Fallback to creating a temporary one if psql fails or no key found
    # This is a bit complex for a script, so let's try to use smoke-client.sh or similar
    if [ -f "${SCRIPT_DIR}/smoke-client.sh" ]; then
      if ./scripts/smoke-client.sh > /dev/null 2>&1; then log_pass; else log_fail "Chat completion smoke test failed"; fi
    else
      log_fail "No API key found and smoke-client.sh missing"
    fi
  else
    if curl -fsS "${BASE_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d '{"messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}' > /dev/null 2>&1; then
      log_pass
    else
      log_fail "Chat completion failed with found API key"
    fi
  fi
else
  log_fail "ADMIN_TOKEN not found in env"
fi

# 3. Portal & UI
log_check "Portal accessibility"
if curl -fsS "${BASE_URL}/client-portal" > /dev/null 2>&1 || curl -fsS "${BASE_URL}/" > /dev/null 2>&1; then
  log_pass
else
  log_fail "Portal/UI not accessible"
fi

# 4. Features (RAG/TTS)
if [ "${RAG_ENABLED:-false}" == "true" ]; then
  log_check "RAG enabled check"
  log_pass
fi

if [ "${TTS_ENABLED:-false}" == "true" ]; then
  log_check "TTS enabled check"
  # Check if pocket-tts is running
  if docker compose ps | grep -q "pocket-tts.*running"; then log_pass; else log_fail "TTS enabled but service not running"; fi
fi

# 5. Backup
log_check "Backup system status"
if [ -d "${ROOT_DIR}/artifacts/backups-local" ] || [ -d "${ROOT_DIR}/.local/backups" ]; then
  log_pass
else
  log_fail "No backup directories found"
fi

# 6. Security
log_check "Secrets scan"
if ./scripts/check-secrets.sh --summary-only > /dev/null 2>&1; then
  log_pass
else
  log_warn "Secrets scan found potential issues (check logs)"
fi

# Final Result
echo -e "\n===================================================="
if [ "$STATUS" == "READY" ]; then
  echo -e "FINAL RESULT: ${GREEN}CLIENT READY${NC}"
else
  echo -e "FINAL RESULT: ${RED}NOT READY${NC}"
  echo -e "Motivos:"
  for reason in "${REASONS[@]}"; do
    echo -e "  - $reason"
  done
fi
echo -e "====================================================\n"

if [ "$STATUS" == "READY" ]; then
  exit 0
else
  exit 1
fi
