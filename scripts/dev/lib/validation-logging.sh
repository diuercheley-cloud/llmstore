#!/usr/bin/env bash

# Validation Logging Library
# Provides standardized logging for validation scripts.

# Colors
export COLOR_RESET='\033[0m'
export COLOR_INFO='\033[0;34m'
export COLOR_OK='\033[0;32m'
export COLOR_WARN='\033[0;33m'
export COLOR_ERROR='\033[0;31m'
export COLOR_STEP='\033[0;36m'
export COLOR_SECTION='\033[1;35m'
export COLOR_CMD='\033[0;90m'

VALIDATION_SCRIPT_NAME=$(basename "$0")

mask_secrets() {
  local input="$1"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

  if [[ -n "${ADMIN_TOKEN:-}" ]]; then
    input="${input//${ADMIN_TOKEN}/[ADMIN_TOKEN_MASKED]}"
  fi
  if [[ -n "${API_KEY:-}" ]]; then
    input="${input//${API_KEY}/[API_KEY_MASKED]}"
  fi
  input=$(echo "$input" | sed -E 's/Bearer [a-zA-Z0-9\._-]+/Bearer [MASKED]/g')
  input=$(echo "$input" | sed -E 's/sk-[a-zA-Z0-9]{12,}/sk-[MASKED]/g')
  input=$(echo "$input" | sed -E 's/eyJ[a-zA-Z0-9\._-]{20,}/eyJ[MASKED]/g')

  if [[ -f "${script_dir}/lib/redaction.sh" ]]; then
    # Use centralized redaction logic
    # We avoid sourcing it here to prevent potential side effects in all scripts
    # but we can use a subshell to get the redacted output
    echo "$input" | (source "${script_dir}/lib/redaction.sh" && redact_stream)
  else
    # Fallback to legacy masking
    echo "$input"
  fi
}

get_timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log_info() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_INFO}INFO${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}"
}

log_ok() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_OK}OK${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}"
}

log_warn() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_WARN}WARN${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}"
}

log_error() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_ERROR}ERROR${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}" >&2
}

log_step() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_STEP}STEP${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}"
}

log_section() {
  local msg
  msg=$(mask_secrets "$1")
  printf "\n${COLOR_SECTION}=== %s ===${COLOR_RESET}\n" "${msg^^}"
}

log_command() {
  local msg
  msg=$(mask_secrets "$1")
  printf "[%s] [%s] ${COLOR_CMD}CMD${COLOR_RESET}: %s\n" "$(get_timestamp)" "${VALIDATION_SCRIPT_NAME}" "${msg}"
}

start_timer() {
  date +%s.%N
}

end_timer() {
  local start_time="$1"
  local end_time
  end_time=$(date +%s.%N)
  local duration
  duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || awk "BEGIN {print $end_time - $start_time}")
  printf "%.3fs" "$duration"
}

write_json_result() {
  local file="$1"
  local step="$2"
  local status="$3"
  local duration="$4"
  local details="$5"
  
  if [[ ! -f "$file" ]]; then
    echo "[]" > "$file"
  fi
  
  local entry
  entry=$(jq -n \
    --arg ts "$(get_timestamp)" \
    --arg script "${VALIDATION_SCRIPT_NAME}" \
    --arg step "$step" \
    --arg status "$status" \
    --arg duration "$duration" \
    --arg details "$details" \
    '{timestamp: $ts, script: $script, step: $step, status: $status, duration: $duration, details: $details}')
    
  local tmp
  tmp=$(mktemp)
  jq ". += [$entry]" "$file" > "$tmp" && mv "$tmp" "$file"
}

# Export functions for use in subshells
export -f mask_secrets get_timestamp log_info log_ok log_warn log_error log_step log_section log_command start_timer end_timer write_json_result
