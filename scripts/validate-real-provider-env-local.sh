#!/bin/bash
set -euo pipefail

# validate-real-provider-env-local.sh
# Validates .env.local safety and configuration for real provider validation.
# Never prints full API keys. Never exposes secrets.
# Returns non-zero if any check fails.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_LOCAL="${PROJECT_ROOT}/.env.local"
ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
GITIGNORE="${PROJECT_ROOT}/.gitignore"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
WARN=0

check_result() {
  local name="$1"
  local status="$2"
  local detail="$3"
  case "$status" in
    PASS) echo -e "  ${GREEN}[PASS]${NC} ${name} — ${detail}" ; PASS=$((PASS+1)) ;;
    FAIL) echo -e "  ${RED}[FAIL]${NC} ${name} — ${detail}" ; FAIL=$((FAIL+1)) ;;
    SKIP) echo -e "  ${YELLOW}[SKIP]${NC} ${name} — ${detail}" ; SKIP=$((SKIP+1)) ;;
    WARN) echo -e "  ${YELLOW}[WARN]${NC} ${name} — ${detail}" ; WARN=$((WARN+1)) ;;
  esac
}

section() {
  echo ""
  echo "================================================"
  echo "  $1"
  echo "================================================"
}

OVERALL_EXIT=0

# Source the helper library
source "${SCRIPT_DIR}/lib/real-provider-env.sh"

section "1. .env.local Existence"

if [[ -f "$ENV_LOCAL" ]]; then
  check_result ".env.local exists" PASS "found at ${PROJECT_ROOT}/.env.local"
else
  check_result ".env.local exists" FAIL "not found — create it: cp .env.example .env.local && edit values"
  OVERALL_EXIT=1
fi

section "2. .env.local in .gitignore"

if grep -qE '^\.env\.local$' "$GITIGNORE" 2>/dev/null || grep -qE '^\.env\.\*$' "$GITIGNORE" 2>/dev/null; then
  check_result ".env.local gitignored" PASS "pattern found in .gitignore"
else
  check_result ".env.local gitignored" FAIL "not found in .gitignore — add .env.local or .env.*"
  OVERALL_EXIT=1
fi

section "3. .env.local Permissions"

local_perms="$(stat -c "%a" "$ENV_LOCAL" 2>/dev/null || echo "000")"
if [[ "$local_perms" == "600" ]] || [[ "$local_perms" == "400" ]]; then
  check_result ".env.local permissions" PASS "permissions ${local_perms} (recommended: 600)"
else
  check_result ".env.local permissions" WARN "permissions ${local_perms} — recommended: 600 (chmod 600 .env.local)"
fi

section "4. Provider Configuration Validation"

# Source the env file into current shell
set -a
source "$ENV_LOCAL"
set +a

PROVIDER_CONFIGS=(
  "OpenAI:OPENAI_PROVIDER_ENABLED:OPENAI_API_KEY:OPENAI_BASE_URL:OPENAI_CHAT_MODEL"
  "DeepSeek:DEEPSEEK_PROVIDER_ENABLED:DEEPSEEK_API_KEY:DEEPSEEK_BASE_URL:DEEPSEEK_CHAT_MODEL"
  "Anthropic:ANTHROPIC_PROVIDER_ENABLED:ANTHROPIC_API_KEY:ANTHROPIC_BASE_URL:ANTHROPIC_MODEL"
)

for config in "${PROVIDER_CONFIGS[@]}"; do
  IFS=':' read -r name enabled_var key_var base_var model_var <<< "$config"

  enabled_val="${!enabled_var:-false}"

  if [[ "$enabled_val" != "true" ]]; then
    check_result "${name}" SKIP "SKIP_PROVIDER_NOT_CONFIGURED — ${enabled_var} is not true"
    continue
  fi

  key_val="${!key_var:-}"
  base_val="${!base_var:-}"
  model_val="${!model_var:-}"

  if [[ -z "$key_val" ]]; then
    check_result "${name}" FAIL "${key_var} is empty but provider is enabled"
    OVERALL_EXIT=1
    continue
  fi

  if [[ -z "$base_val" ]]; then
    check_result "${name} base URL" WARN "${base_var} is empty — will use default"
  fi

  if [[ -z "$model_val" ]]; then
    check_result "${name} model" WARN "${model_var} is empty — will use provider default"
  fi

  masked="$(mask_provider_key "$key_val")"
  check_result "${name}" PASS "enabled, key ${masked}, base=${base_val}"
done

section "5. REAL_PROVIDER_VALIDATION_ENABLED Guard"

val_enabled="${REAL_PROVIDER_VALIDATION_ENABLED:-false}"
if [[ "$val_enabled" == "true" ]] || [[ "$val_enabled" == "1" ]]; then
  check_result "REAL_PROVIDER_VALIDATION_ENABLED" PASS "enabled — real outbound calls allowed"
else
  check_result "REAL_PROVIDER_VALIDATION_ENABLED" WARN "disabled — real provider calls blocked (opt-in required)"
fi

section "6. Max Cost Configuration"

max_cost="${REAL_PROVIDER_MAX_COST_BRL:-}"
if [[ -n "$max_cost" ]]; then
  if [[ "$max_cost" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    check_result "REAL_PROVIDER_MAX_COST_BRL" PASS "configured at R$ ${max_cost}"
  else
    check_result "REAL_PROVIDER_MAX_COST_BRL" WARN "invalid number: ${max_cost}"
  fi
else
  check_result "REAL_PROVIDER_MAX_COST_BRL" WARN "not set — no cost limit enforced"
fi

section "7. No Real Keys in .env.example"

if [[ -f "$ENV_EXAMPLE" ]]; then
  leaks=0
  if grep -qE '^OPENAI_API_KEY=[a-zA-Z0-9]' "$ENV_EXAMPLE" 2>/dev/null; then
    check_result "OPENAI_API_KEY in .env.example" FAIL "found a real-looking key"
    leaks=1
  fi
  if grep -qE '^DEEPSEEK_API_KEY=[a-zA-Z0-9]' "$ENV_EXAMPLE" 2>/dev/null; then
    check_result "DEEPSEEK_API_KEY in .env.example" FAIL "found a real-looking key"
    leaks=1
  fi
  if grep -qE '^ANTHROPIC_API_KEY=[a-zA-Z0-9]' "$ENV_EXAMPLE" 2>/dev/null; then
    check_result "ANTHROPIC_API_KEY in .env.example" FAIL "found a real-looking key"
    leaks=1
  fi
  if [[ "$leaks" -eq 0 ]]; then
    check_result ".env.example keys empty" PASS "no real API keys in .env.example"
  else
    OVERALL_EXIT=1
  fi
else
  check_result ".env.example" SKIP ".env.example not found — skipping"
fi

section "8. No Real Keys in artifacts/"

if [[ -d "$ARTIFACTS_DIR" ]] && [[ "$(ls -A "$ARTIFACTS_DIR" 2>/dev/null)" ]]; then
  if assert_no_provider_key_leak "$ARTIFACTS_DIR" "\.env\.example"; then
    check_result "artifacts/ clean" PASS "no real API keys in artifacts/"
  else
    check_result "artifacts/ clean" FAIL "potential key leak in artifacts/"
    OVERALL_EXIT=1
  fi
else
  check_result "artifacts/ clean" SKIP "artifacts/ empty or does not exist"
fi

section "Summary"

echo ""
echo "  ${GREEN}PASS${NC}: ${PASS}  ${RED}FAIL${NC}: ${FAIL}  ${YELLOW}SKIP${NC}: ${SKIP}  ${YELLOW}WARN${NC}: ${WARN}"
echo ""

if [[ "$OVERALL_EXIT" -eq 0 ]]; then
  echo -e "${GREEN}All real provider env checks passed.${NC}"
else
  echo -e "${RED}Some checks failed. Review above before using real providers.${NC}"
fi

exit "$OVERALL_EXIT"
