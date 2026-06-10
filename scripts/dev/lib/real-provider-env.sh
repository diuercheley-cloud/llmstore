#!/usr/bin/env bash
# lib/real-provider-env.sh
# Helper library for real provider validation.
# Sources .env.local and exposes functions to check provider config safely.
# NEVER prints full API keys — always uses mask_provider_key.
# Meant to be sourced by validation scripts. Does NOT set -euo pipefail
# (that's the caller's responsibility) to avoid side effects.

# Internal paths (namespaced to avoid collisions with sourcing scripts)
__RP_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__RP_PROJECT_ROOT="$(cd "$__RP_LIB_DIR/../.." && pwd)"

__RP_ENV_LOCAL="${__RP_PROJECT_ROOT}/.env.local"
__RP_ENV_EXAMPLE="${__RP_PROJECT_ROOT}/.env.example"

# ── Load helpers ──────────────────────────────────────────────
if [[ -f "${__RP_LIB_DIR}/validation-logging.sh" ]]; then
  source "${__RP_LIB_DIR}/validation-logging.sh"
fi

# ── Load .env.local ───────────────────────────────────────────
load_real_provider_env() {
  if [[ ! -f "$__RP_ENV_LOCAL" ]]; then
    log_error ".env.local not found at ${__RP_ENV_LOCAL}"
    return 1
  fi
  set -a
  source "$__RP_ENV_LOCAL"
  set +a
}

# ── Guard: is real provider validation enabled? ──────────────
is_real_provider_validation_enabled() {
  local val="${REAL_PROVIDER_VALIDATION_ENABLED:-false}"
  [[ "$val" == "true" ]] || [[ "$val" == "1" ]]
}

# ── Mask an API key for safe display ─────────────────────────
mask_provider_key() {
  local key="$1"
  local len=${#key}
  if [[ "$len" -le 8 ]]; then
    echo "********"
    return
  fi
  echo "${key:0:4}****${key:len-4}"
}

# ── Require provider key if provider is enabled ──────────────
# Usage: require_provider_key_if_enabled PROVIDER_NAME ENABLED_VAR_NAME KEY_VAR_NAME
require_provider_key_if_enabled() {
  local provider_name="$1"
  local enabled_var_name="$2"
  local key_var_name="$3"

  local enabled_val="${!enabled_var_name:-false}"
  local key_val="${!key_var_name:-}"

  if [[ "$enabled_val" == "true" ]]; then
    if [[ -z "$key_val" ]]; then
      log_error "${provider_name} is enabled but ${key_var_name} is empty"
      return 1
    fi
    log_ok "${provider_name}: key present (${key_var_name})"
  fi
  return 0
}

# ── Get max cost BRL with fallback ────────────────────────────
get_real_provider_max_cost_brl() {
  echo "${REAL_PROVIDER_MAX_COST_BRL:-2.00}"
}

# ── Assert no provider key leak in given paths ───────────────
assert_no_provider_key_leak() {
  local scan_path="$1"
  local exclude_pattern="${2:-}"

  if [[ ! -e "$scan_path" ]]; then
    return 0
  fi

  local key_patterns=(
    "OPENAI_API_KEY=[a-zA-Z0-9].*"
    "DEEPSEEK_API_KEY=[a-zA-Z0-9].*"
    "ANTHROPIC_API_KEY=[a-zA-Z0-9].*"
    "sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"
  )

  local found=0
  for pattern in "${key_patterns[@]}"; do
    local matches
    if [[ -n "$exclude_pattern" ]]; then
      matches="$(grep -rnE "$pattern" "$scan_path" 2>/dev/null | grep -vE "$exclude_pattern" || true)"
    else
      matches="$(grep -rnE "$pattern" "$scan_path" 2>/dev/null || true)"
    fi
    if [[ -n "$matches" ]]; then
      log_error "Potential key leak in ${scan_path}: matched pattern ${pattern}"
      echo "$matches" | while IFS= read -r line; do
        log_warn "  ${line}"
      done
      found=1
    fi
  done

  return $found
}

export -f load_real_provider_env is_real_provider_validation_enabled mask_provider_key
export -f require_provider_key_if_enabled get_real_provider_max_cost_brl
export -f assert_no_provider_key_leak
