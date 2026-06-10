#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
cd "${ROOT_DIR}"

listener_pids=()

cleanup() {
  local pid
  for pid in "${listener_pids[@]}"; do
    kill "${pid}" >/dev/null 2>&1 || true
    wait "${pid}" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

latest_summary_file() {
  local latest_dir
  latest_dir="$(ls -td "${ROOT_DIR}"/artifacts/dr-tests-local/* 2>/dev/null | head -n1)"
  if [[ -n "${latest_dir}" && -f "${latest_dir}/summary.txt" ]]; then
    printf '%s\n' "${latest_dir}/summary.txt"
  fi
}

summary_value() {
  local summary_file="$1"
  local key="$2"
  awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "${summary_file}"
}

assert_summary_value() {
  local summary_file="$1"
  local key="$2"
  local expected="$3"
  local actual
  actual="$(summary_value "${summary_file}" "${key}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "[test-dr-local-port-selection][error] ${key} expected=${expected} actual=${actual}" >&2
    exit 1
  fi
}

assert_summary_has_key() {
  local summary_file="$1"
  local key="$2"
  if [[ -z "$(summary_value "${summary_file}" "${key}")" ]]; then
    echo "[test-dr-local-port-selection][error] missing ${key} in ${summary_file}" >&2
    exit 1
  fi
}

assert_no_project_orphans() {
  local summary_file="$1"
  local project_name
  project_name="$(summary_value "${summary_file}" PROJECT_NAME)"
  if [[ -z "${project_name}" ]]; then
    echo "[test-dr-local-port-selection][error] missing PROJECT_NAME in ${summary_file}" >&2
    exit 1
  fi
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${project_name}-"; then
    echo "[test-dr-local-port-selection][error] orphan containers found for ${project_name}" >&2
    docker ps -a --filter "name=${project_name}" --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}' >&2
    exit 1
  fi
}

start_listener() {
  local port="$1"
  python3 -m http.server "${port}" --bind 127.0.0.1 >/dev/null 2>&1 &
  local pid=$!
  listener_pids+=("${pid}")
  sleep 1
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

run_default_auto() {
  local output summary_file
  output="$(RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" 2>&1)"
  printf '%s\n' "${output}"
  summary_file="$(printf '%s\n' "${output}" | awk -F= '/^\[dr-test-local\] report=/{print $2}' | tail -n1)"
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    summary_file="$(latest_summary_file)"
  fi
  assert_summary_has_key "${summary_file}" DR_HOST_PORT
  assert_summary_has_key "${summary_file}" BASE_URL
  assert_summary_value "${summary_file}" PORT_SELECTION_MODE auto
  assert_summary_value "${summary_file}" PORT_VALIDATION_STATUS ok
  assert_no_project_orphans "${summary_file}"
  printf '[test-dr-local-port-selection] auto_summary=%s\n' "${summary_file}"
}

run_manual_free() {
  local output summary_file
  output="$(DR_HOST_PORT=18123 RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" 2>&1)"
  printf '%s\n' "${output}"
  summary_file="$(printf '%s\n' "${output}" | awk -F= '/^\[dr-test-local\] report=/{print $2}' | tail -n1)"
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    summary_file="$(latest_summary_file)"
  fi
  assert_summary_value "${summary_file}" DR_HOST_PORT 18123
  assert_summary_value "${summary_file}" BASE_URL http://127.0.0.1:18123
  assert_summary_value "${summary_file}" PORT_SELECTION_MODE manual
  assert_summary_value "${summary_file}" PORT_VALIDATION_STATUS ok
  assert_no_project_orphans "${summary_file}"
  printf '[test-dr-local-port-selection] manual_summary=%s\n' "${summary_file}"
}

run_manual_occupied() {
  local output status summary_file
  start_listener 18124 || true
  set +e
  output="$(DR_HOST_PORT=18124 RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" 2>&1)"
  status=$?
  set -e
  printf '%s\n' "${output}"
  if [[ "${status}" -eq 0 ]]; then
    echo "[test-dr-local-port-selection][error] occupied manual port should fail" >&2
    exit 1
  fi
  if ! printf '%s\n' "${output}" | grep -q 'DR_HOST_PORT=18124 is already in use'; then
    echo "[test-dr-local-port-selection][error] missing clear occupied-port error" >&2
    exit 1
  fi
  summary_file="$(latest_summary_file)"
  assert_summary_value "${summary_file}" DR_HOST_PORT 18124
  assert_summary_value "${summary_file}" PORT_SELECTION_MODE manual
  assert_summary_value "${summary_file}" PORT_VALIDATION_STATUS failed
  assert_summary_value "${summary_file}" PORT_VALIDATION_ERROR port_allocated
  assert_no_project_orphans "${summary_file}"
  printf '[test-dr-local-port-selection] occupied_summary=%s\n' "${summary_file}"
}

run_auto_with_18081_occupied() {
  local output summary_file selected_port
  start_listener 18081 || true
  output="$(RAG_INDEX_TIMEOUT_SECONDS=1 "${SCRIPT_DIR}/dr-test-local.sh" 2>&1)"
  printf '%s\n' "${output}"
  summary_file="$(printf '%s\n' "${output}" | awk -F= '/^\[dr-test-local\] report=/{print $2}' | tail -n1)"
  if [[ -z "${summary_file}" || ! -f "${summary_file}" ]]; then
    summary_file="$(latest_summary_file)"
  fi
  selected_port="$(summary_value "${summary_file}" DR_HOST_PORT)"
  if [[ "${selected_port}" == "18081" ]]; then
    echo "[test-dr-local-port-selection][error] auto mode selected occupied 18081" >&2
    exit 1
  fi
  assert_summary_value "${summary_file}" PORT_SELECTION_MODE auto
  assert_summary_value "${summary_file}" PORT_VALIDATION_STATUS ok
  assert_no_project_orphans "${summary_file}"
  printf '[test-dr-local-port-selection] auto_18081_occupied_summary=%s\n' "${summary_file}"
}

run_default_auto
run_manual_free
run_manual_occupied
run_auto_with_18081_occupied

printf '[test-dr-local-port-selection] success\n'
