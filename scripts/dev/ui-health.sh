#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

check_ui_pattern() {
  local path="$1"
  local pattern="$2"
  local description="$3"
  printf '[ui-health] Checking %s for %s... ' "${path}" "${description}"
  local response
  response="$(curl -fsS "${BASE_URL}${path}")"
  if grep -q "${pattern}" <<<"${response}"; then
    printf 'OK\n'
  else
    printf 'FAILED (pattern "%s" not found)\n' "${pattern}"
    exit 1
  fi
}

check_ui_not_pattern() {
  local path="$1"
  local pattern="$2"
  local description="$3"
  printf '[ui-health] Checking %s for absence of %s... ' "${path}" "${description}"
  local response
  response="$(curl -fsS "${BASE_URL}${path}")"
  if grep -q "${pattern}" <<<"${response}"; then
    printf 'FAILED (pattern "%s" found, should NOT be there)\n' "${pattern}"
    exit 1
  else
    printf 'OK\n'
  fi
}

# Client Portal Checks
check_ui_pattern "/client-portal" "View Technical Response (JSON)" "Debug button"
check_ui_pattern "/client-portal" "sk-..." "API key placeholder"
check_ui_not_pattern "/client-portal" "pre id=\"me\"" "old raw JSON element"

# Admin Dashboard Checks
check_ui_pattern "/admin-dashboard" "toggleDebug" "Debug toggle function"
check_ui_pattern "/admin-dashboard" "System Health <button" "Health debug button"
check_ui_not_pattern "/admin-dashboard" "<pre id=\"healthDeep\">carregando...</pre>" "old raw JSON placeholder"

# Admin Lab Checks
check_ui_pattern "/admin-lab" "Clientes" "Admin Lab clients tab"
check_ui_pattern "/admin-lab" "runFlow('client-full')" "Admin Lab financial flow action"

printf '[ui-health] UI Health checks passed!\n'
