#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_env_file() {
  local env_path="$1"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ -z "${line}" ]] || [[ "${line}" =~ ^[[:space:]]*# ]]; then
      continue
    fi
    if [[ "${line}" != *=* ]]; then
      continue
    fi
    local key="${line%%=*}"
    local value="${line#*=}"
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
  if [[ "${BONSAI_ENABLED:-false}" == "true" ]]; then
    DOCKER_COMPOSE_ARGS+=(--profile bonsai)
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
  if [[ -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
    compose_args+=(-p "${COMPOSE_PROJECT_NAME}")
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

curl_base_url() {
  local url="$1"
  shift
  local curl_status=0
  if [[ "${url}" == https://localhost* ]] || [[ "${url}" == https://127.0.0.1* ]]; then
    curl -k "$@" "${url}" || curl_status=$?
  else
    curl "$@" "${url}" || curl_status=$?
  fi
  if [[ "${curl_status}" -eq 0 ]]; then
    return 0
  fi

  if [[ "${curl_status}" -eq 7 ]] && { [[ "${url}" == http://localhost* ]] || [[ "${url}" == http://127.0.0.1* ]]; }; then
    local internal_url="${url}"
    internal_url="${internal_url/http:\/\/localhost:${HOST_PORT:-18080}/http://localhost:8080}"
    internal_url="${internal_url/http:\/\/127.0.0.1:${HOST_PORT:-18080}/http://localhost:8080}"
    dc exec -T control-plane curl "$@" "${internal_url}"
    return $?
  fi

  return "${curl_status}"
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
  curl_base_url "${base_url}/admin/api-keys" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${demo_client_id}\",\"name\":\"${key_name}\"}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])'
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
