#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure scripts directory is in PYTHONPATH for Python utilities
export PYTHONPATH="${ROOT_DIR}/scripts:${PYTHONPATH:-}"

# Load operator errors library if available
if [[ -f "${ROOT_DIR}/scripts/lib/operator-errors.sh" ]]; then
  source "${ROOT_DIR}/scripts/lib/operator-errors.sh"
fi

CURL_BASE_URL_LAST_MODE="uninitialized"
CURL_BASE_URL_LAST_URL=""

record_curl_mode() {
  local mode="$1"
  local url="${2:-}"
  CURL_BASE_URL_LAST_MODE="${mode}"
  CURL_BASE_URL_LAST_URL="${url}"
  if [[ -n "${VALIDATION_CURL_MODE_FILE:-}" ]]; then
    printf '%s\n' "${mode}" >> "${VALIDATION_CURL_MODE_FILE}"
  fi
}

load_env_file() {
  local env_path="$1"
  local preserve_existing="${STACK_ENV_PRESERVE_EXISTING:-false}"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ -z "${line}" ]] || [[ "${line}" =~ ^[[:space:]]*# ]]; then
      continue
    fi
    if [[ "${line}" != *=* ]]; then
      continue
    fi
    local key="${line%%=*}"
    local value="${line#*=}"
    if [[ "${preserve_existing}" == "true" && -v "${key}" ]]; then
      continue
    fi
    export "${key}=${value}"
  done < "${env_path}"
}

resolve_stack_env_file() {
  if [[ -n "${ENV_FILE:-}" ]]; then
    printf '%s\n' "${ENV_FILE}"
    return
  fi
  case "${STACK_MODE:-local}" in
    prod)
      if [[ -f "${ROOT_DIR}/.env.prod" ]]; then
        printf '%s\n' ".env.prod"
        return
      fi
      ;;
    *)
      if [[ -f "${ROOT_DIR}/.env.local" ]]; then
        printf '%s\n' ".env.local"
        return
      fi
      if [[ -f "${ROOT_DIR}/.env" ]]; then
        printf '%s\n' ".env"
        return
      fi
      ;;
  esac
  printf '%s\n' ".env.example"
}

init_stack_env() {
  STACK_ENV_FILE="$(resolve_stack_env_file)"
  export STACK_ENV_FILE
  local stack_env_path
  if [[ "${STACK_ENV_FILE}" = /* ]]; then
    stack_env_path="${STACK_ENV_FILE}"
  else
    stack_env_path="${ROOT_DIR}/${STACK_ENV_FILE}"
  fi
  if [[ -f "${stack_env_path}" ]]; then
    set -a
    load_env_file "${stack_env_path}"
    set +a
  fi
  DOCKER_COMPOSE_ARGS=(--env-file "${stack_env_path}" -f "${ROOT_DIR}/docker-compose.yml")
  if [[ "${STACK_MODE:-local}" == "prod" ]]; then
    DOCKER_COMPOSE_ARGS+=(-f "${ROOT_DIR}/docker-compose.prod.yml")
  fi
  if [[ -n "${EXTRA_COMPOSE_FILES:-}" ]]; then
    for compose_file in ${EXTRA_COMPOSE_FILES}; do
      if [[ "${compose_file}" = /* ]]; then
        DOCKER_COMPOSE_ARGS+=(-f "${compose_file}")
      else
        DOCKER_COMPOSE_ARGS+=(-f "${ROOT_DIR}/${compose_file}")
      fi
    done
  fi
}

dc() {
  local compose_args=()
  local compose_project_name="${COMPOSE_PROJECT_NAME:-llm-inference-stack}"
  if [[ -n "${compose_project_name}" ]]; then
    compose_args+=(-p "${compose_project_name}")
  fi
  docker compose "${compose_args[@]}" "${DOCKER_COMPOSE_ARGS[@]}" "$@"
}

default_base_url() {
  if [[ "${STACK_MODE:-local}" == "prod" ]]; then
    if [[ -n "${SERVER_NAME:-}" && "${SERVER_NAME}" != "localhost" ]]; then
      printf 'https://%s\n' "${SERVER_NAME}"
      return
    fi
    printf 'https://localhost:%s\n' "${PROXY_HTTPS_PORT:-443}"
    return
  fi
  printf 'http://localhost:%s\n' "${HOST_PORT:-18080}"
}

http_get_ok() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "${url}" >/dev/null 2>&1
    return $?
  fi

  python3 - "${url}" <<'PY' >/dev/null 2>&1
import sys
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url, timeout=5) as response:
    if response.status < 200 or response.status >= 400:
        raise SystemExit(1)
PY
}

curl_base_url() {
  local url="$1"
  shift
  local curl_status=0
  record_curl_mode "host_attempt" "${url}"
  if [[ "${url}" == https://localhost* ]] || [[ "${url}" == https://127.0.0.1* ]]; then
    curl -k "$@" "${url}" || curl_status=$?
  else
    curl "$@" "${url}" || curl_status=$?
  fi
  if [[ "${curl_status}" -eq 0 ]]; then
    record_curl_mode "host" "${url}"
    return 0
  fi

  if [[ "${curl_status}" -eq 7 ]] && { [[ "${url}" == http://localhost* ]] || [[ "${url}" == http://127.0.0.1* ]]; }; then
    local internal_url="${url}"
    internal_url="${internal_url/http:\/\/localhost:${HOST_PORT:-18080}/http://localhost:8080}"
    internal_url="${internal_url/http:\/\/127.0.0.1:${HOST_PORT:-18080}/http://localhost:8080}"
    if curl "$@" "${internal_url}"; then
      record_curl_mode "container_local" "${internal_url}"
      return 0
    fi
    if dc exec -T control-plane curl "$@" "${internal_url}"; then
      record_curl_mode "container" "${internal_url}"
      return 0
    fi
    record_curl_mode "container_error" "${internal_url}"
    return $?
  fi

  record_curl_mode "host_error" "${url}"
  return "${curl_status}"
}

curl_mode_label() {
  case "${CURL_BASE_URL_LAST_MODE:-unknown}" in
    host)
      printf 'host'
      ;;
    container)
      printf 'container-fallback'
      ;;
    *)
      printf '%s' "${CURL_BASE_URL_LAST_MODE:-unknown}"
      ;;
  esac
}

log_curl_mode() {
  local url="$1"
  local target="${2:-$url}"
  local message="validated ${target} via $(curl_mode_label)"
  if declare -F log_info >/dev/null 2>&1; then
    log_info "${message}"
  else
    printf '[curl_base_url] %s\n' "${message}"
  fi
}

lookup_demo_client_id() {
  local base_url="${1:-$(default_base_url)}"
  local admin_token="${ADMIN_TOKEN:-}"
  [[ -n "${admin_token}" ]] || return 1
  curl_base_url "${base_url}/admin/clients" -fsS -H "X-Admin-Token: ${admin_token}" | python3 -c '
import json, sys
clients = json.load(sys.stdin)
for item in clients:
    if item["name"] == "demo-client":
        print(item["id"])
        break
'
}

issue_demo_api_key() {
  local base_url="${1:-$(default_base_url)}"
  local key_name="${2:-script-access}"
  local demo_client_id
  demo_client_id="$(lookup_demo_client_id "${base_url}")" || return 1
  [[ -n "${demo_client_id}" ]] || return 1
  issue_api_key_for_client_id "${base_url}" "${demo_client_id}" "${key_name}"
}

issue_api_key_for_client_id() {
  local base_url="${1:-$(default_base_url)}"
  local client_id="${2:?client_id is required}"
  local key_name="${3:-script-access}"
  curl_base_url "${base_url}/admin/api-keys" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"${key_name}\"}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])'
}

lookup_first_active_agent_tenant_id() {
  local base_url="${1:-$(default_base_url)}"
  local admin_token="${ADMIN_TOKEN:-}"
  [[ -n "${admin_token}" ]] || return 1
  curl_base_url "${base_url}/admin/agents" -fsS -H "X-Admin-Token: ${admin_token}" | python3 -c '
import json, sys
agents = json.load(sys.stdin)
for item in agents:
    if item.get("status") == "active" and item.get("tenant_id"):
        print(item["tenant_id"])
        break
'
}

require_api_key() {
  local base_url="${1:-$(default_base_url)}"
  local key_name="${2:-script-access}"
  if [[ -n "${API_KEY:-}" ]]; then
    printf '%s\n' "${API_KEY}"
    return 0
  fi
  issue_demo_api_key "${base_url}" "${key_name}"
}
