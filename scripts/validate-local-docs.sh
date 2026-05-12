#!/usr/bin/env bash

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/validation-logging.sh"
init_stack_env

# Configuration
PORT="${PORT:-${HOST_PORT:-8000}}"
URL="${BASE_URL:-$(default_base_url)}/developer-docs"

log_section "Local Developer Documentation Validation"

# Fetch documentation
log_step "Fetching $URL"
CONTENT=$(curl_base_url "$URL" -s -f)

if [ -n "$CONTENT" ]; then
  log_curl_mode "$URL"
  log_ok "Successfully fetched documentation"
else
  log_error "Failed to fetch documentation or it's empty"
  exit 1
fi

# Check for some expected content
log_step "Checking for expected content"
EXPECTED_STRINGS=("Documentation" "API" "Introduction")
for str in "${EXPECTED_STRINGS[@]}"; do
  if echo "$CONTENT" | grep -qi "$str"; then
    log_ok "Found expected string: $str"
  else
    log_warn "Could not find expected string: $str"
  fi
done

log_ok "Documentation validation completed successfully"
